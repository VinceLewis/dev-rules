# Bash rules

Adds to `dev_rules.md` for shell scripts and shell steps in CI.

## When to use shell

- Use Bash only to glue commands together. Rewrite in Python 3 (standard library only, like `scripts/size_gate.py`) when a script exceeds about 100 lines, needs arrays of records, parses JSON beyond one `jq` call, or needs tests with many cases.
- Keep CI `run:` steps to 3 lines or fewer; move longer logic into a script file that runs locally too.

## Layout

- Put scripts in `scripts/`, named with a verb (`scripts/build.sh`), executable, starting with `#!/usr/bin/env bash`.
- Each script starts with `set -euo pipefail` and `IFS=$'\n\t'`.
- Wrap the body in `main() { … }` and end with `main "$@"`.

## Tooling

- Lint: `shellcheck` on every `*.sh` file and on `.githooks/pre-commit` in CI, with no blanket disables; each `# shellcheck disable=` names the rule and gives a reason.
- Format: `shfmt -d -i 2 -ci` in CI. `shfmt` does not wrap long lines; break them with `\` at argument boundaries, and the size gate enforces the width.
- Test: a script containing `if`, `case` or a loop gets a `bats-core` test in `tests/<script>.bats`, run by `bats tests/` in CI and one at a time with `bats --filter '<name>' tests/<script>.bats`; other scripts are tested by the CI step that uses them.
- Target Bash 5 with GNU coreutils on Linux (`ubuntu-latest`). macOS is not supported.

## Code

- Quote every expansion: `"$var"`, `"$@"`, `"$(cmd)"`. Use `[[ … ]]` for tests and `$(…)` for substitution.
- Check required commands and variables first: `command -v jq >/dev/null || die "jq required"`, `: "${DB_URL:?DB_URL is required}"`.
- Create temporary files inside one directory: `tmp=$(mktemp -d)`, removed by `trap 'rm -rf "$tmp"' EXIT`.
- Write errors to stderr and exit non-zero; define one `die()` helper.
- Pass arguments as arrays (`args=(--flag "$value"); cmd "${args[@]}"`), never by building a command string for `eval`.
- Use `--` before user-supplied paths to stop option parsing.
- Read secrets from environment variables, never from command-line arguments (visible in `ps`).

## Pitfalls

- `local x=$(cmd)` hides the failure of `cmd`; declare first, then assign.
- `set -e` is ignored inside functions called in `if`, `&&`, `||` or `!` contexts.
- Parsing `ls` output; use a glob; to recurse, use `find -print0` with `while IFS= read -r -d ''`.
- `cd` without `|| exit`; run it in a subshell: `(cd -- "$dir" && cmd)`.
- `rm -rf "$dir/"` with an unset `$dir`; `set -u` and `${dir:?}` guard it.
- `echo` with options or backslashes; use `printf '%s\n'`.
