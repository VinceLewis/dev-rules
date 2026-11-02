# Publish this repository to GitHub

## Inputs

- The working tree of this repository: @"dev_rules.md", the `dev_rules_*.md` stack files and `.prompts/`.

## Task

1. If there is no Git repository yet, run `git init -b main`.
2. Commit every file in the working tree.
3. If `VinceLewis/<repo-name>` does not exist, create it as a public repository with `gh repo create VinceLewis/<repo-name> --public --source . --push`; otherwise push `main`.

## Constraints

- Commit nothing outside the repository (no scratchpad backups) and no secrets.
- Do not force-push.

## Output

- The repository URL and the pushed commit hash.
