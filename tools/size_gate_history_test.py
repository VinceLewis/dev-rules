"""Seam: the size gate's history tests (--commits, --ratchet) and the pre-commit hook test; size_gate_test.py the rest.
Canonical as dev-rules tools/size_gate_history_test.py, copied unchanged to scripts/size_gate_history_test.py.
"""

import json
import shutil
import subprocess
import sys

from size_gate_test import GATE, GIT, GIT_ENV, HERE, HOOK, RepositoryCase


class HistoryTest(RepositoryCase):
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

    def test_deleting_a_test_is_not_a_test_change(self) -> None:
        base = self.commit("Add the app", {})
        (self.root / "tests/app_test.py").unlink()
        self.commit("Change the code, delete its test", {"src/app.py": "A = 1\n"})
        self.assert_gate(1, "--commits", f"{base}..HEAD", says="'Change the code, delete its test'")

    def test_a_root_commit_from_an_unrelated_history_is_checked(self) -> None:
        base = self.commit("Add the app", {})
        blob = self.git("hash-object", "-w", "--stdin", stdin="X = 1\n").strip()
        source = self.git("mktree", stdin=f"100644 blob {blob}\torphan.py\n").strip()
        tree = self.git("mktree", stdin=f"040000 tree {source}\tsrc\n").strip()
        orphan = self.git("commit-tree", tree, "-m", "Orphan code").strip()
        self.git("merge", "-q", "--allow-unrelated-histories", "-m", "Merge the orphan", orphan)
        self.assert_gate(1, "--commits", f"{base}..HEAD", says="'Orphan code': changes product code")

    def test_commit_ranges_must_be_two_commits(self) -> None:
        base = self.commit("Add the app", {})
        for commits in ["HEAD", "..HEAD", "HEAD..", f"{base}...HEAD", "nosuch..HEAD", f"{base}..nosuch"]:
            with self.subTest(commits):
                self.assert_gate(2, "--commits", commits, says="SETUP: --commits")

    def test_ratchet_sets_budgets_to_actual_plus_15_percent_and_prints_changes(self) -> None:
        self.write({"src/big.py": "x = 1\n" * 320})
        legacy = {"src/big.py": {"lines": 330, "wide_lines": 0}, "src/app.py": {"lines": 2, "wide_lines": 0}}
        caps = {"max_product_code_lines": 1000, "max_test_code_lines": 3, "max_total_lines": 1000}
        self.budget(**caps, legacy=legacy, reasons=["2026-11-03 budget for § 4"])
        result = self.run_gate("--ratchet")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        for line in [
            "lowered max_product_code_lines 1000 -> 370",
            "raised max_test_code_lines 3 -> 5",
            "lowered legacy src/big.py to 320 lines, 0 wide",
            "lowered legacy src/app.py: entry removed",
        ]:
            self.assertIn(line, result.stdout)
        text = (self.root / "size-budget.json").read_text(encoding="utf-8")
        self.assertIn("2026-11-03 budget for § 4", text)
        budget = json.loads(text)
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

    def test_ratchet_refuses_to_raise_a_legacy_figure(self) -> None:
        self.write({"src/big.py": "x = 1\n" * 320 + "#" * 121 + "\n"})
        for name, figures in [("lines grew", (310, 1)), ("wide lines grew", (321, 0))]:
            with self.subTest(name):
                legacy = {"src/big.py": {"lines": figures[0], "wide_lines": figures[1]}}
                self.budget(max_product_code_lines=1000, max_total_lines=1000, legacy=legacy)
                before = (self.root / "size-budget.json").read_text(encoding="utf-8")
                says = f"refused legacy raise src/big.py: 321 lines, 1 wide; recorded {figures[0]}, {figures[1]}"
                self.assert_gate(1, "--ratchet", says=says)
                self.assertEqual(before, (self.root / "size-budget.json").read_text(encoding="utf-8"))


class HookTest(RepositoryCase):
    """The hook runs the gate, then gitleaks on the staged changes; without python3 or gitleaks it is SETUP."""

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
        (self.bin / "python3").unlink()
        result = self.run_hook(0)
        self.assertEqual((2, "SETUP: python3 is not installed\n"), (result.returncode, result.stderr))
