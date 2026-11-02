# Add the 500-line hard cap per source file

## Inputs

- @"dev_rules.md" sections 4 and 5. Section 4 already sets a per-file budget of 300 lines that the ratchet can raise.

## Task

1. Section 4: no source file exceeds 500 lines, so an LLM agent can read and edit the whole file in one pass. The
   per-file budget never ratchets or is raised past 500; split the file by responsibility instead. Source files are
   product code, test code, scripts and CI files; docs, data, test data, generated and lock files are exempt.
2. Section 5: the size gate fails on any source file over 500 lines, whatever `size-budget.json` says.

## Constraints

- One way per rule; no duplicated rule text across files.
- Lines at most 120 characters.

## Output

- The diff, committed and pushed to `main`.
