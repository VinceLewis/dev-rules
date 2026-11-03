#!/usr/bin/env python3
"""Tests for the size gate and the pre-commit hook (dev_rules.md section 5): each check fails on its seeded breach in
a temporary Git repository, and a clean repository passes. This file holds the shared repository case and the budget
and per-file tests; size_gate_scan_test.py the scans, commits, ratchet and hook. Running this file runs both.
Canonical as dev-rules tools/size_gate_test.py, copied unchanged to scripts/size_gate_test.py.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE / "size_gate.py"
HOOK = HERE / "pre-commit" if (HERE / "pre-commit").exists() else HERE.parent / ".githooks" / "pre-commit"
CLEAN_ENV = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}  # not a hook's repo
GIT = shutil.which("git") or "git"
GIT_ENV = {
    **CLEAN_ENV,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}
BUDGET = {
    "classes": {
        "generated": ["*.lock"],
        "build": ["size-budget.json", "pyproject.toml", ".gitignore", "scripts/*", ".githooks/*"],
        "product": ["src/*"],
        "test_code": ["tests/*.py", "tests/*.bats"],
        "test_data": ["tests/data/*"],
        "docs": ["*.md", "docs/*"],
    },
    "max_tracked_files": 20,
    "max_total_lines": 400,
    "max_product_code_lines": 100,
    "max_test_code_lines": 100,
    "max_test_data_files": 5,
    "max_test_data_lines": 20,
    "max_docs_lines": 50,
    "max_scope_lines": 300,
    "max_file_lines": 300,
    "max_line_width": 120,
    "max_projects": 1,
    "max_interfaces": 0,
    "allowed_top_level": [".githooks", "docs", "scripts", "src", "tests"],
    "literal_scan_allow": [{"reason": "the column name is the product's vocabulary", "values": ["amount"]}],
    "legacy": {},
    "reasons": ["2026-11-03 test budget"],
}
FILES = {
    ".gitignore": "__pycache__/\n",  # dev_rules.md section 6; importing size_gate_checks writes bytecode
    "pyproject.toml": '[project]\nname = "demo"\n',
    "src/app.py": 'def sum_amounts(rows):\n    return sum(row["amount"] for row in rows)\n',
    "tests/app_test.py": "import unittest\n\n\nclass AppTest(unittest.TestCase):\n    pass\n",
    "tests/data/input.csv": "code,amount\nA001,10.50\n",
    "tests/data/expected.json": '{"total": "10.50", "currency": "EUR"}\n',
    "docs/scope.md": "# Scope\n",
    "README.md": "# Demo\n",
}


class RepositoryCase(unittest.TestCase):
    """A temporary Git repository holding a small clean project and its budget."""

    def setUp(self) -> None:
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.git("init", "-q", "-b", "main")
        self.write(FILES)
        self.budget()

    def git(self, *args: str) -> str:
        return subprocess.run(  # noqa: S603 - fixed argv to git, no shell
            [GIT, *args], cwd=self.root, env=GIT_ENV, check=True, capture_output=True, text=True
        ).stdout

    def write(self, files: dict[str, str]) -> None:
        for path, text in files.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text, encoding="utf-8")

    def budget(self, **changes: object) -> None:
        self.write({"size-budget.json": json.dumps({**BUDGET, **changes}, indent=2) + "\n"})

    def commit(self, subject: str, files: dict[str, str]) -> str:
        self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)
        return self.git("rev-parse", "HEAD").strip()

    def run_gate(self, *args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603 - fixed argv to the gate, no shell
            [sys.executable, str(GATE), *args], cwd=cwd or self.root, env=GIT_ENV, capture_output=True, text=True
        )

    def assert_gate(self, code: int, *args: str, says: str = "") -> None:
        result = self.run_gate(*args)
        output = result.stdout + result.stderr
        self.assertEqual(code, result.returncode, output)
        self.assertIn(says, output)


class GateTest(RepositoryCase):
    def test_clean_repository_passes(self) -> None:
        self.assert_gate(0, says="size gate: PASS")

    def test_setup_outside_a_git_repository(self) -> None:
        outside = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        result = self.run_gate(cwd=outside)
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("SETUP:", result.stderr)

    def test_setup_when_the_budget_is_missing_or_invalid(self) -> None:
        cases = {
            "missing": None,
            "not JSON": "{",
            "unknown key": json.dumps({**BUDGET, "max_widgets": 1}),
            "missing key": json.dumps({key: value for key, value in BUDGET.items() if key != "legacy"}),
            "file cap above 500": json.dumps({**BUDGET, "max_file_lines": 501}),
            "allow group without reason": json.dumps({**BUDGET, "literal_scan_allow": [{"values": ["amount"]}]}),
            "legacy without wide lines": json.dumps({**BUDGET, "legacy": {"src/app.py": {"lines": 2}}}),
        }
        for name, text in cases.items():
            with self.subTest(name):
                (self.root / "size-budget.json").unlink(missing_ok=True)
                if text is not None:
                    self.write({"size-budget.json": text})
                self.assert_gate(2, says="SETUP: size-budget.json")

    def test_each_budget_fails_when_exceeded(self) -> None:
        self.write({"src/shape.py": "from typing import Protocol\n\n\nclass Shape(Protocol):\n    pass\n"})
        self.budget(max_interfaces=1)
        self.assert_gate(0)
        keys = [
            "max_tracked_files",
            "max_total_lines",
            "max_product_code_lines",
            "max_test_code_lines",
            "max_test_data_files",
            "max_test_data_lines",
            "max_docs_lines",
            "max_scope_lines",
            "max_projects",
            "max_interfaces",
        ]
        for key in keys:
            with self.subTest(key):
                self.budget(**{"max_interfaces": 1, key: 0})
                self.assert_gate(1, says=f"FAIL {key}: ")

    def test_slice_specs_are_outside_the_docs_budget(self) -> None:
        self.budget(max_docs_lines=2)
        self.write({"docs/slice-9.md": "spec line\n" * 40})
        self.assert_gate(0)
        self.write({"docs/notes.md": "note\n"})
        self.assert_gate(1, says="FAIL max_docs_lines: 3 > 2")

    def test_unclassified_file_and_unknown_top_level_directory_fail(self) -> None:
        self.write({"notes.txt": "a note\n"})
        self.assert_gate(1, says="notes.txt: matches no class")
        (self.root / "notes.txt").unlink()
        self.write({"tools/readme.md": "# Tools\n"})
        self.assert_gate(1, says="top-level directory 'tools' is not in allowed_top_level")

    def test_forbidden_paths_fail(self) -> None:
        paths = [
            "src/app-v2.py",
            "src/app_old.py",
            "src/app.py.bak",
            "src/app.py.orig",
            "src/app.py.txt",
            "docs/llm-routes.json",
            "docs/evidence/run.md",
            "docs/handoffs/next.md",
            "docs/ledger/state.md",
            "src/tool.exe",
            "src/lib.dll",
            "src/lib.so",
            "docs/spec.docx",
            "tests/data/input.xlsx",
            "docs/spec.pdf",
            "src/db.dump",
            "src/db.backup",
            "src/backup-2026.sql",
        ]
        for path in paths:
            with self.subTest(path):
                self.write({path: "x\n"})
                self.assert_gate(1, says=f"FAIL {path}: forbidden")
                (self.root / path).unlink()

    def test_source_file_over_max_file_lines_fails(self) -> None:
        self.budget(max_product_code_lines=1000, max_total_lines=1000)
        self.write({"src/big.py": "x = 1\n" * 300})
        self.assert_gate(0)
        self.write({"src/big.py": "x = 1\n" * 301})
        self.assert_gate(1, says="src/big.py: 301 lines > max_file_lines 300")

    def test_wide_code_line_fails_but_prose_and_json_are_exempt(self) -> None:
        self.write(
            {
                "src/wide.py": "x = 1  #" + "-" * 112 + "\n",
                "README.md": "# Demo " + "-" * 200 + "\n",
                "scripts/settings.json": '{"key": "' + "v" * 200 + '"}\n',
            }
        )
        self.assert_gate(0)
        self.write({"src/wide.py": "x = 1  #" + "-" * 113 + "\n"})
        self.assert_gate(1, says="src/wide.py:1: wider than max_line_width 120")

    def test_legacy_figures_must_equal_actual(self) -> None:
        self.write({"src/big.py": "x = 1\n" * 309 + "#" * 121 + "\n"})
        recorded = {"src/big.py": {"lines": 310, "wide_lines": 1}}
        cases = [
            ("recorded figures", recorded, 0, "PASS"),
            ("file grew", {"src/big.py": {"lines": 309, "wide_lines": 1}}, 1, "must equal actual: 310 lines, 1 wide"),
            ("lines figure above actual", {"src/big.py": {"lines": 311, "wide_lines": 1}}, 1, "must equal actual"),
            ("wide lines grew", {"src/big.py": {"lines": 310, "wide_lines": 0}}, 1, "must equal actual"),
            ("wide figure above actual", {"src/big.py": {"lines": 310, "wide_lines": 2}}, 1, "must equal actual"),
            ("file complies", {**recorded, "src/app.py": {"lines": 2, "wide_lines": 0}}, 1, "src/app.py: complies"),
            ("file missing", {**recorded, "src/gone.py": {"lines": 600, "wide_lines": 0}}, 1, "src/gone.py: legacy"),
        ]
        for name, legacy, code, says in cases:
            with self.subTest(name):
                self.budget(max_product_code_lines=1000, max_total_lines=1000, legacy=legacy)
                self.assert_gate(code, says=says)


if __name__ == "__main__":
    # Discovery imports this file and size_gate_scan_test.py as modules, so each test runs once.
    pattern = "size_gate*test.py"
    unittest.main(module=None, argv=[sys.argv[0], "discover", "--start-directory", str(HERE), "--pattern", pattern])
