# Add the parallel-build rule

## Inputs

- `dev_rules.md` section 14 (AI agents).
- Evidence: @"/home/vince/projects/work/edgeIT/onboarding/AGENTS.md" Workflow section, where shared-core slices were
  built serially and independent work (a new UI project, packets behind a committed skeleton) in parallel.

## Task

Add to section 14: the three conditions for building in parallel (disjoint files in separate worktrees, a committed
contract first, one-at-a-time merges with the full gate), serial shared-core work, parallel read-only reviews, and the
skeleton-then-packets pattern.

## Output

- The diff, committed and pushed.
