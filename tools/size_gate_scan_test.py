"""Seam: the size gate's scan, commit and ratchet tests and the pre-commit hook test; size_gate_test.py the rest.
Canonical as dev-rules tools/size_gate_scan_test.py, copied unchanged to scripts/size_gate_scan_test.py.
"""

import json
import shutil
import subprocess
import sys

from size_gate_test import GATE, GIT, GIT_ENV, HERE, HOOK, RepositoryCase


class ScanTest(RepositoryCase):
    def test_literal_scan_finds_test_data_in_product_code(self) -> None:
        self.write({"tests/data/seed.sql": "INSERT INTO account (code, balance) VALUES ('Z900', 77.25);\n"})
        self.assert_gate(0)
        for literal in ['"A001"', '"EUR"', 'row["currency"]', "10.50", '"Z900"', "77.25"]:
            with self.subTest(literal):
                self.write({"src/extra.py": f"VALUE = {literal}\n"})
                self.assert_gate(1, says="hard-coded test-data value")

    def test_suspect_product_literals_fail(self) -> None:
        # Split so that secret scanners do not flag this file.
        literals = [
            '"Server=db;Database=app;"',
            '"postgres' + '://db/app"',
            '"/home/alice/input.csv"',
            '"10.0.0.7"',
            '"' + "ab" * 32 + '"',
            "PASS" + 'WORD = "hunter' + '22"',
            '"-----BEGIN RSA ' + 'PRIVATE KEY-----"',
        ]
        for literal in literals:
            with self.subTest(literal):
                self.write({"src/extra.py": f"VALUE = {literal}\n"})
                self.assert_gate(1, says="suspect")

    def test_skip_and_focus_markers_in_test_code_fail(self) -> None:
        markers = [
            't.Skip("later")',
            '[Fact(Skip = "later")]',
            'Assert.Skip("later")',
            "@pytest.mark.skip",
            'pytest.skip("later")',
            "@pytest.mark.xfail",
            "it.skip('x')",
            "it.only('x')",
            "it.todo('x')",
        ]
        for marker in markers:
            with self.subTest(marker):
                self.write({"tests/extra_test.py": f"{marker}\n"})
                self.assert_gate(1, says="tests/extra_test.py:1: skip or focus marker")
        (self.root / "tests/extra_test.py").unlink()
        self.write({"tests/app.bats": '@test "sums" {\n  skip\n}\n'})
        self.assert_gate(1, says="tests/app.bats:2: skip or focus marker")

    def test_commits_that_change_product_code_need_test_code(self) -> None:
        base = self.commit("Add the app", {})
        self.commit("Add a test with the code", {"src/app.py": "A = 1\n", "tests/app_test.py": "B = 1\n"})
        self.commit("Refactor: rename", {"src/app.py": "A = 2\n"})
        self.git("checkout", "-q", "-b", "side")
        self.commit("Side change", {"src/side.py": "S = 1\n", "tests/side_test.py": "T = 1\n"})
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "Merge side", "side")
        self.assert_gate(0, "--commits", f"{base}..HEAD")
        self.commit("Change the code alone", {"src/app.py": "A = 3\n"})
        self.assert_gate(1, "--commits", f"{base}..HEAD", says="'Change the code alone': changes product code")
        self.assert_gate(2, "--commits", "HEAD", says="SETUP: --commits needs a range")
        self.assert_gate(2, "--commits", "nosuch..HEAD", says="SETUP: git rev-list")

    def test_ratchet_sets_budgets_to_actual_plus_15_percent_and_prints_changes(self) -> None:
        self.write({"src/big.py": "x = 1\n" * 320})
        legacy = {"src/big.py": {"lines": 330, "wide_lines": 0}, "src/app.py": {"lines": 2, "wide_lines": 0}}
        self.budget(max_product_code_lines=1000, max_test_code_lines=3, max_total_lines=1000, legacy=legacy)
        result = self.run_gate("--ratchet")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        for line in [
            "lowered max_product_code_lines 1000 -> 370",
            "raised max_test_code_lines 3 -> 5",
            "lowered legacy src/big.py to 320 lines, 0 wide",
            "lowered legacy src/app.py: entry removed",
        ]:
            self.assertIn(line, result.stdout)
        budget = json.loads((self.root / "size-budget.json").read_text(encoding="utf-8"))
        self.assertEqual({"src/big.py": {"lines": 320, "wide_lines": 0}}, budget["legacy"])
        self.assertEqual(
            (370, 5, 300, 120, 300),
            (
                budget["max_product_code_lines"],
                budget["max_test_code_lines"],
                budget["max_file_lines"],
                budget["max_line_width"],
                budget["max_scope_lines"],
            ),
        )
        self.assertRegex(budget["reasons"][-1], r"^\d{4}-\d{2}-\d{2} --ratchet to actual \+ 15%: .*raised max_test_c")
        self.assert_gate(0)
        self.assert_gate(2, "--ratchet", "--commits", "HEAD..HEAD", says="not allowed with argument")


class HookTest(RepositoryCase):
    """The hook runs the gate, then gitleaks on the staged changes; without gitleaks it is SETUP."""

    def setUp(self) -> None:
        super().setUp()
        self.bin = self.root / ".git" / "test-bin"
        self.bin.mkdir()
        (self.bin / "git").symlink_to(GIT)
        (self.bin / "python3").symlink_to(sys.executable)
        self.write(
            {
                "scripts/size_gate.py": GATE.read_text(encoding="utf-8"),
                "scripts/size_gate_checks.py": (HERE / "size_gate_checks.py").read_text(encoding="utf-8"),
                ".githooks/pre-commit": HOOK.read_text(encoding="utf-8"),
            }
        )
        self.budget(max_total_lines=1000)

    def run_hook(self, gitleaks_exit: int | None) -> subprocess.CompletedProcess:
        if gitleaks_exit is not None:
            self.write_tool("gitleaks", f'printf \'%s \' "$@" > "$0.args"\nexit {gitleaks_exit}\n')
        bash = shutil.which("bash") or "bash"
        env = {**GIT_ENV, "PATH": str(self.bin)}
        return subprocess.run(  # noqa: S603 - fixed argv to the hook, no shell
            [bash, ".githooks/pre-commit"], cwd=self.root, env=env, capture_output=True, text=True
        )

    def write_tool(self, name: str, body: str) -> None:
        (self.bin / name).write_text("#!/bin/sh\n" + body, encoding="utf-8")
        (self.bin / name).chmod(0o755)

    def test_hook(self) -> None:
        result = self.run_hook(None)
        self.assertEqual((2, "SETUP: gitleaks is not installed\n"), (result.returncode, result.stderr))
        result = self.run_hook(0)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("git --pre-commit --staged ", (self.bin / "gitleaks.args").read_text(encoding="utf-8"))
        self.assertEqual(1, self.run_hook(1).returncode)
        self.write({"notes.txt": "a note\n"})
        self.assertEqual(1, self.run_hook(0).returncode)
