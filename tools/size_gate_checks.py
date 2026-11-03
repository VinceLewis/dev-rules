"""Seam: reads the repository and runs the per-file, scan and commit checks; size_gate.py holds the rest.
Canonical as dev-rules tools/size_gate_checks.py, copied unchanged to scripts/size_gate_checks.py.
"""

import contextlib
import csv
import dataclasses
import fnmatch
import json
import pathlib
import re
import shutil
import subprocess

CLASSES = ("generated", "build", "product", "test_code", "test_data", "docs")  # the first class that matches wins
SOURCE_CLASSES = ("product", "test_code", "build")
DATA_SUFFIXES = {".json", ".xml", ".md", ".config", ".csproj", ".fsproj", ".props", ".targets", ".slnx", ".resx"}
FORBIDDEN_NAMES = (  # copies, generated indexes, binaries, office documents, dumps and backups
    "*-v[0-9]*.*",
    "*_old.*",
    "*.bak",
    "*.orig",
    "*.*.txt",
    "*llm-routes*.json",
    "*.exe",
    "*.dll",
    "*.so",
    "*.docx",
    "*.xlsx",
    "*.pdf",
    "*.dump",
    "*.backup",
    "*backup*.sql",
)
FORBIDDEN_DIRS = {"evidence", "handoff", "handoffs", "ledger", "ledgers"}
SUSPECT = {  # product string literals that hold data or secrets
    "connection string": re.compile(r"""(?i)["'][^"'\n]*\b(?:server|data source|host|user id|password)\s*=[^"'\n]*;"""),
    "connection URL": re.compile(r"""(?i)["'](?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|sqlserver)://"""),
    "absolute path": re.compile(r"""["'](?:/home/|/Users/|/tmp/|/etc/|/var/|/opt/|/root/|[A-Za-z]:\\)"""),
    "IP address": re.compile(r"""["'][^"'\n]*?(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"""),
    "64-character hex hash": re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])"),
    "secret": re.compile(r"""(?i)\b(?:password|passwd|secret|api_?key|access_?token)["']?\s*[:=]\s*["'][^"'\s]{4,}"""),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
SKIP_MARKER = re.compile(
    r"\bt\.Skip|\bSkip\s*=(?!=)|\bAssert\.Skip|\bpytest\.mark\.skip|\bpytest\.skip\("
    r"|\bpytest\.mark\.xfail|\.skip\(|\.only\(|\.todo\("
)
BATS_SKIP = re.compile(r"\s*skip\b")
QUOTED = re.compile(r"""'([^'\n]*)'|"([^"\n]*)\"""")
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")


class SetupError(Exception):
    """The gate could not run: not a Git repository, or the budget file is missing or invalid."""


@dataclasses.dataclass(frozen=True, slots=True)
class Entry:
    path: str
    cls: str | None
    lines: list[str]
    text: str
    is_source: bool  # product, test code, scripts and CI files; never data, docs or generated files
    wide: list[int]  # numbers of the source lines wider than max_line_width


def git(root: pathlib.Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise SetupError("git is not installed")
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv to git, no shell
            [executable, *args], cwd=root, check=True, capture_output=True, text=True
        )
        return completed.stdout
    except subprocess.CalledProcessError as err:
        raise SetupError(f"git {' '.join(args)}: {err.stderr.strip()}") from err


def classify(path: str, classes: dict) -> str | None:
    return next((cls for cls in CLASSES if any(fnmatch.fnmatchcase(path, glob) for glob in classes[cls])), None)


def list_entries(root: pathlib.Path, budget: dict) -> list[Entry]:
    listed = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    entries = []
    for path in sorted({path for path in listed if path and (root / path).is_file()}):
        cls = classify(path, budget["classes"])
        lines = [line.decode("utf-8", "replace") for line in (root / path).read_bytes().splitlines()]
        is_source = cls in SOURCE_CLASSES and pathlib.PurePath(path).suffix not in DATA_SUFFIXES
        width = budget["max_line_width"]
        wide = [number for number, line in enumerate(lines, 1) if is_source and len(line) > width]
        entries.append(Entry(path, cls, lines, "\n".join(lines), is_source, wide))
    return entries


def check_files(entries: list[Entry], budget: dict) -> list[str]:
    errors = []
    cap = budget["max_file_lines"]
    legacy = budget["legacy"]
    for entry in entries:
        path, count, wide = entry.path, len(entry.lines), entry.wide
        directories = path.split("/")[:-1]
        if entry.cls is None:
            errors.append(f"{path}: matches no class in size-budget.json")
        if directories and directories[0] not in budget["allowed_top_level"]:
            errors.append(f"{path}: top-level directory {directories[0]!r} is not in allowed_top_level")
        if any(fnmatch.fnmatchcase(pathlib.PurePath(path).name, glob) for glob in FORBIDDEN_NAMES):
            errors.append(f"{path}: forbidden file name (copy, backup, binary, office document or dump)")
        if FORBIDDEN_DIRS & set(directories):
            errors.append(f"{path}: forbidden directory (evidence, handoff or ledger)")
        if entry.cls == "product":
            errors += [f"{path}: suspect {name} literal" for name, regex in SUSPECT.items() if regex.search(entry.text)]
        if entry.cls == "test_code":
            is_bats = path.endswith(".bats")
            for number, line in enumerate(entry.lines, 1):
                if SKIP_MARKER.search(line) or is_bats and BATS_SKIP.match(line):
                    errors.append(f"{path}:{number}: skip or focus marker")
        if path in legacy:
            figures = legacy[path]
            if (figures["lines"], figures["wide_lines"]) != (count, len(wide)):
                errors.append(f"{path}: legacy figures must equal actual: {count} lines, {len(wide)} wide")
            if count <= cap and not wide:
                errors.append(f"{path}: complies; remove its legacy entry")
            continue
        if entry.is_source and count > cap:
            errors.append(f"{path}: {count} lines > max_file_lines {cap}")
        errors += [f"{path}:{number}: wider than max_line_width {budget['max_line_width']}" for number in wide]
    sources = {entry.path for entry in entries if entry.is_source}
    errors += [f"{path}: legacy entry for a missing or non-source file" for path in legacy if path not in sources]
    return errors


def check_literal_scan(entries: list[Entry], budget: dict) -> list[str]:
    """Fail on any key or value of 3 or more characters from test data that appears in product code: JSON keys and
    values, CSV cells, and quoted strings and numbers in other text files. A dotted value also gives its parts."""
    values: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            values.update(node)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, (str, int, float)) and not isinstance(node, bool):
            values.add(str(node))

    for entry in [entry for entry in entries if entry.cls == "test_data"]:
        suffix = pathlib.PurePath(entry.path).suffix
        if suffix == ".json":
            with contextlib.suppress(json.JSONDecodeError):  # invalid JSON test data is read as other text below
                walk(json.loads(entry.text))
                continue
        if suffix in (".csv", ".tsv"):
            for row in csv.reader(entry.lines, delimiter="\t" if suffix == ".tsv" else ","):
                values.update(row)
            continue
        values.update(first or second for first, second in QUOTED.findall(entry.text))
        values.update(NUMBER.findall(entry.text))
    parts = {part.strip() for value in values for part in [value, *value.split(".")]}
    allowed = {value for group in budget["literal_scan_allow"] for value in group["values"]}
    product = [entry for entry in entries if entry.cls == "product"]
    errors = []
    for value in sorted(part for part in parts - allowed if len(part) >= 3):
        pattern = re.compile(r"(?<![\w.])" + re.escape(value) + r"(?!\w)")
        found = [entry.path for entry in product if pattern.search(entry.text)]
        if found:
            errors.append(f"hard-coded test-data value {value!r} in {', '.join(found)}")
    return errors


def check_commits(root: pathlib.Path, commits: str, classes: dict) -> list[str]:
    """Test with code: each non-merge commit that changes product code changes test code too, or says Refactor:."""
    if ".." not in commits:
        raise SetupError(f"--commits needs a range A..B, not {commits!r}")
    errors = []
    for sha in git(root, "rev-list", "--no-merges", commits).split():
        subject = git(root, "log", "-1", "--format=%s", sha).strip()
        paths = git(root, "diff-tree", "-z", "--root", "--no-commit-id", "--name-only", "-r", sha).split("\0")
        changed = {classify(path, classes) for path in paths if path}
        if "product" in changed and "test_code" not in changed and not subject.startswith("Refactor:"):
            errors.append(f"commit {sha[:12]} {subject!r}: changes product code but no test code")
    return errors
