# Add the line-width and no-compression rules

## Inputs

- `dev_rules.md` sections 4, 5 and 12, and each stack file's formatter rule.
- Evidence: @"/home/vince/projects/work/edgeIT/onboarding/size-budget.json" and its size gate, where line budgets were
  met by 278 lines over 120 characters.

## Task

1. Section 4: add a line-width budget (120 characters); the slice estimate is the budget; budgets limit bloat, not
   readability, so never compress to fit.
2. Section 5: the size gate fails on code and CI lines wider than the budget; data files, prose and test data are exempt.
3. Section 12: revert simplifications that save lines by making code harder to read.
4. Stack files: set each formatter's width to 120 where it has one; where it does not wrap, say the gate enforces it.
5. Add the evidence to "Anti-patterns seen".

## Constraints

- One way per rule; no duplicated rule text across files.

## Output

- The diff, committed and pushed.
