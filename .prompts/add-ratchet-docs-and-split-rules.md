# Automate the ratchet, exclude slice specs from the docs budget, and name split seams

## Inputs

- `dev_rules.md` sections 4 and 5.
- Evidence: @"/home/vince/projects/work/edgeIT/onboarding/size-budget.json" reasons, where every slice needed caps
  edited by hand, specs committed before code hit the docs cap, and a 300-line limit forced one class across three
  files.

## Task

1. Section 4: `--ratchet` at merge replaces hand-edited caps; temporary slice specs are outside the docs budget; a file
   over the limit splits only along a seam named at the top of the new file, never just to get under the limit.
2. Section 5: add the `--ratchet` behaviour to the gate's list.

## Output

- The diff, committed and pushed.
