# Commit and push one file

## Inputs

- Repository: `<repo>`. File: `<path>`, for example @"/home/vince/projects/personal/giggle-new/claude-findings.md".

## Task

1. Check the branch and what is already staged. Commit only `<path>`, using `git commit -- <path>`, so other staged or modified files stay as they are.
2. Push the current branch to its upstream.

## Constraints

- No force-push, and never `--no-verify`. If a hook blocks the push, stop and report its output.
- End the commit message with the session's attribution line.

## Output

- The commit hash, the branch, and the push result.
