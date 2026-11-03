#!/usr/bin/env python3
"""The size gate (dev_rules.md sections 4 and 5): measure the repository and enforce size-budget.json.
This file holds the command line, the budget file, the measures and the ratchet; size_gate_checks.py the checks.
Canonical as dev-rules tools/size_gate.py, copied unchanged to scripts/size_gate.py. Exit 0 pass, 1 fail, 2 SETUP.
"""

import argparse
import datetime
import fnmatch
import json
import os
import pathlib
import re
import sys

from size_gate_checks import (
    CLASSES,
    Entry,
    SetupError,
    check_commits,
    check_files,
    check_literal_scan,
    check_paths,
    git,
    list_entries,
    list_paths,
)

COUNT_BUDGETS = (
    "max_tracked_files",
    "max_total_lines",
    "max_product_code_lines",
    "max_test_code_lines",
    "max_test_data_files",
    "max_test_data_lines",
    "max_docs_lines",
    "max_projects",
    "max_interfaces",
)
FIXED_BUDGETS = ("max_scope_lines", "max_file_lines", "max_line_width")  # rule values: never ratcheted
KEYS = {"classes", *COUNT_BUDGETS, *FIXED_BUDGETS, "allowed_top_level", "literal_scan_allow", "legacy", "reasons"}
FILE_LINES_LIMIT = 500
HEADROOM_PERCENT = 15
SLICE_SPEC = re.compile(r"docs/slice-\d+\.md")
PROJECT_FILES = ("*.csproj", "*.fsproj", "go.mod", "package.json", "pyproject.toml")
MODIFIERS = r"^[ \t]*(?:(?:public|internal|private|protected|export|default|declare|sealed|partial|abstract)[ \t]+)*"
INTERFACE = re.compile(  # declarations at the start of a line, so comments that say "interface" do not count
    MODIFIERS + r"(?:interface[ \t]+\w+|abstract[ \t]+(?:partial[ \t]+)?(?:class|record)\b)"  # C#, TypeScript
    r"|^[ \t]*type[ \t]+\w+[ \t]+interface\b"  # Go
    r"|^[ \t]*class[ \t]+\w+[ \t]*\([^)]*\b(?:ABC|ABCMeta|Protocol)\b",  # Python
    re.MULTILINE,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SetupError(f"size-budget.json: {message}")


def is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def load_budget(path: pathlib.Path) -> dict:
    try:
        budget = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise SetupError(f"{path.name} not found at the repository root") from err
    except (json.JSONDecodeError, UnicodeDecodeError) as err:
        raise SetupError(f"{path.name} is not valid JSON: {err}") from err
    require(isinstance(budget, dict), "must be a JSON object")
    require(not KEYS - budget.keys(), f"missing keys {sorted(KEYS - budget.keys())}")
    require(not budget.keys() - KEYS, f"unknown keys {sorted(budget.keys() - KEYS)}")
    classes = budget["classes"]
    require(isinstance(classes, dict) and set(classes) == set(CLASSES), f"classes must have exactly {list(CLASSES)}")
    require(all(is_strings(globs) for globs in classes.values()), "each class is a list of globs")
    require(all(is_count(budget[key]) for key in COUNT_BUDGETS + FIXED_BUDGETS), "each max_* is a whole number")
    require(budget["max_file_lines"] <= FILE_LINES_LIMIT, f"max_file_lines is never raised past {FILE_LINES_LIMIT}")
    require(is_strings(budget["allowed_top_level"]), "allowed_top_level is a list of names")
    require(is_strings(budget["reasons"]), "reasons is a list of dated lines")
    require(isinstance(budget["literal_scan_allow"], list), "literal_scan_allow is a list of {reason, values}")
    for group in budget["literal_scan_allow"]:
        require(isinstance(group, dict) and set(group) == {"reason", "values"}, "allow groups are {reason, values}")
        require(isinstance(group["reason"], str) and group["reason"].strip() != "", "each allow group has a reason")
        require(is_strings(group["values"]), "allow values are strings")
    require(isinstance(budget["legacy"], dict), "legacy maps a path to {lines, wide_lines}")
    for figures in budget["legacy"].values():
        require(isinstance(figures, dict) and set(figures) == {"lines", "wide_lines"}, "legacy is {lines, wide_lines}")
        require(is_count(figures["lines"]) and is_count(figures["wide_lines"]), "legacy figures are whole numbers")
    return budget


def measure(entries: list[Entry]) -> dict:
    lines = {cls: sum(len(entry.lines) for entry in entries if entry.cls == cls) for cls in CLASSES}
    product = [entry for entry in entries if entry.cls == "product"]
    docs = [entry for entry in entries if entry.cls == "docs" and not SLICE_SPEC.fullmatch(entry.path)]
    names = [pathlib.PurePath(entry.path).name for entry in entries]
    return {
        "max_tracked_files": len(entries),
        "max_total_lines": sum(len(entry.lines) for entry in entries),
        "max_product_code_lines": lines["product"],
        "max_test_code_lines": lines["test_code"],
        "max_test_data_files": sum(1 for entry in entries if entry.cls == "test_data"),
        "max_test_data_lines": lines["test_data"],
        "max_docs_lines": sum(len(entry.lines) for entry in docs),
        "max_projects": sum(1 for name in names if any(fnmatch.fnmatchcase(name, g) for g in PROJECT_FILES)),
        "max_interfaces": sum(len(INTERFACE.findall(entry.text)) for entry in product),
        "max_scope_lines": next((len(entry.lines) for entry in entries if entry.path == "docs/scope.md"), 0),
    }


def ratchet(root: pathlib.Path, budget: dict, entries: list[Entry], actual: dict) -> int:
    """Every count budget to actual plus 15%, every legacy figure down to actual, and a dated reason line.
    A legacy figure may only fall: if a file grew past its entry, nothing is written and the exit is 1."""
    sources = {entry.path: entry for entry in entries if entry.is_source}
    refused = []
    for path, figures in budget["legacy"].items():
        entry = sources.get(path)
        if entry and (len(entry.lines) > figures["lines"] or len(entry.wide) > figures["wide_lines"]):
            refused.append(
                f"refused legacy raise {path}: {len(entry.lines)} lines, {len(entry.wide)} wide; "
                f"recorded {figures['lines']}, {figures['wide_lines']}"
            )
    if refused:
        print("\n".join(refused))
        return 1
    changes = []
    for key in COUNT_BUDGETS:
        new = actual[key] + actual[key] * HEADROOM_PERCENT // 100
        if new != budget[key]:
            changes.append(f"{'raised' if new > budget[key] else 'lowered'} {key} {budget[key]} -> {new}")
        budget[key] = new
    cap = budget["max_file_lines"]
    for path, figures in list(budget["legacy"].items()):
        entry = sources.get(path)
        if entry is None or len(entry.lines) <= cap and not entry.wide:
            del budget["legacy"][path]
            changes.append(f"lowered legacy {path}: entry removed")
        elif (len(entry.lines), len(entry.wide)) != (figures["lines"], figures["wide_lines"]):
            budget["legacy"][path] = {"lines": len(entry.lines), "wide_lines": len(entry.wide)}
            changes.append(f"lowered legacy {path} to {len(entry.lines)} lines, {len(entry.wide)} wide")
    for change in changes:
        print(change)
    today = datetime.date.today().isoformat()
    budget["reasons"].append(f"{today} --ratchet to actual + {HEADROOM_PERCENT}%: {'; '.join(changes) or 'no change'}")
    (root / "size-budget.json").write_text(json.dumps(budget, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


def report(entries: list[Entry], actual: dict, budget: dict, errors: list[str]) -> None:
    print(f"{'class':<14}{'files':>7}{'lines':>9}")
    for cls in (*CLASSES, None):
        members = [entry for entry in entries if entry.cls == cls]
        print(f"{cls or 'unclassified':<14}{len(members):>7}{sum(len(entry.lines) for entry in members):>9}")
    for key in (*COUNT_BUDGETS, "max_scope_lines"):
        print(f"{key:<24}{actual[key]:>9} of {budget[key]}")
    for error in errors:
        print("FAIL", error)
    print(f"size gate: FAIL ({len(errors)})" if errors else "size gate: PASS")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure the repository and enforce size-budget.json.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--commits", metavar="A..B", help="also check each non-merge commit in the range")
    mode.add_argument("--ratchet", action="store_true", help="rewrite size-budget.json to actual and exit 0")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace")  # file names need not be UTF-8
    try:
        root = pathlib.Path(os.fsdecode(git(pathlib.Path.cwd(), "rev-parse", "--show-toplevel")).rstrip("\n"))
        budget = load_budget(root / "size-budget.json")
        paths = list_paths(root)
        entries = list_entries(root, paths, budget)
        actual = measure(entries)
        if args.ratchet:
            return ratchet(root, budget, entries, actual)
        errors = check_paths(root, paths, budget) + check_files(entries, budget) + check_literal_scan(entries, budget)
        errors += [
            f"{key}: {actual[key]} > {budget[key]}"
            for key in (*COUNT_BUDGETS, "max_scope_lines")
            if actual[key] > budget[key]
        ]
        if args.commits:
            errors += check_commits(root, args.commits, budget["classes"])
    except SetupError as err:
        print(f"SETUP: {err}", file=sys.stderr)
        return 2
    report(entries, actual, budget, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
