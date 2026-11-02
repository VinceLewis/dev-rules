# Adopt three-valued verdicts, gate negative controls and a strict legacy ratchet

## Inputs

- @"/home/vince/Downloads/2026-11-02-dev-rules-proposals.md": four proposals; adopt three, reject capability homes.
- @"dev_rules.md" adoption step 5 and sections 4, 5, 8 and 13.

## Task

1. Section 8: every check (tests, size gate, pre-commit hook, each CI step) ends as pass, fail or `SETUP:`.
   `SETUP:` means the check could not run; it exits non-zero and is never green.
2. Section 5: the size gate ships with `scripts/size_gate_test.py`, standard-library `unittest`, the same file in
   every repository. For each check it builds a temporary Git repository with one seeded breach and asserts exit 1;
   a clean repository exits 0. Section 13 runs it in CI before the size gate.
3. Section 4: in an existing repository, the adoption commit records each file that breaches the 500-line cap or
   the line width under `legacy` in `size-budget.json`, by path, with its line count and wide-line count. Each
   figure may only fall; the gate fails when a file exceeds its figures or a figure exceeds the actual value, so it
   is lowered in the change that earned it. The entry goes when the file complies. A new entry after adoption is a
   budget raise. Section 5 checks 9 and 10 honour these entries. Adoption step 5 points to section 4.
4. Do not add capability homes or any register, evidence or gate-record files.
5. Section 4: the rule that the lines-per-file budget is never raised past 500 names `legacy` entries as the only
   exception.
6. Section 5: raise the size gate's line guide from about 150 to about 200 lines, to fit the `legacy` handling and
   check 11. Its test file does not count towards it.

## Constraints

- One way per rule; no duplicated rule text across files.
- Lines at most 120 characters.

## Output

- The diff, committed and pushed to `main`.
