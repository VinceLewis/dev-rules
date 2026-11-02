# Development rules

Goal: simple, short, working code from the first commit. Every rule is imperative and checkable; where a machine can check it, CI does.

Every rule names one way to do a thing. Never offer or pick an alternative. When a choice comes up that no rule covers, ask the owner, then add the answer to these files.

## Adopting these rules

1. Copy `dev_rules.md` and the stack files you use into `docs/rules/`.
2. Import them from `CLAUDE.md`, one line each, for example: `@docs/rules/dev_rules.md` and `@docs/rules/dev_rules_dotnet.md`.
3. Add the size gate (section 5), the pre-commit hook (section 6) and the CI workflow (section 13) in the first commit, before any feature code.
4. Delete the stack files you do not use. Project-specific rules go in `CLAUDE.md`, never in these files.

## Index

| File | Applies when the repository contains |
|---|---|
| `dev_rules_dotnet.md` | `*.csproj`, `*.slnx` or `*.cs` |
| `dev_rules_sqlserver.md` | T-SQL scripts, SQL Server connection code or an `mssql` container |
| `dev_rules_postgres.md` | PostgreSQL schema, migrations or driver code |
| `dev_rules_sqlite.md` | an embedded SQLite database or `*.db` file in use |
| `dev_rules_go.md` | `go.mod` |
| `dev_rules_typescript.md` | `package.json` or `tsconfig.json` |
| `dev_rules_python.md` | `pyproject.toml` or `*.py` beyond a one-file script |
| `dev_rules_bash.md` | any `*.sh` file or shell step in CI longer than 3 lines |

Stack files only add or specialise; when a stack file and this file seem to conflict, the stack file wins for that stack.

## 1. Scope

- Build one vertical slice end to end first: input, core logic, output, and a test that runs the whole path. A layer with no caller is not progress.
- Reject unsupported inputs, options and modes explicitly, before any side effect. Do not half-support them.
- Keep the scope in `docs/scope.md`. Write every deferral there as `Deferred: <feature>. Trigger: <event that brings it back>.` No trigger, no deferral: drop it.
- Before each new slice, add its scope, size estimate and budget increase to `docs/scope.md` and get approval before any code.

## 2. KISS and YAGNI

- Name the requirement or reproduced bug before adding any complexity. If you cannot, do not add it.
- No interface, abstract base, wrapper, factory, adapter or plug-in point without two real implementations or callers today. Test doubles do not count unless the real dependency is unusable in tests.
- No extra project, package, module or service until one would exceed its size budget or needs a separate deployment.
- No configuration option without a user who sets it to two different values.
- Use the standard library and the platform's built-in features. Where a stack file names a third-party package as the standard, use that package; never write your own or choose a different one.
- Prefer one longer obvious function over five short indirect ones; split on reuse or the file limit, not on taste.
- Synchronous and in-process first. Queues, brokers, caches and background workers need a measured reason.

## 3. No hard-coding

- Product code must not contain names, values, counts, totals, hashes, paths, URLs or connection strings that belong to data. They come from input data, command-line flags or environment variables. Secrets and connection strings come from environment variables only.
- Hard-coded data is allowed only in tests and test data.
- Product code never reads from test folders and never branches on "test mode". Allow at most one named, internal fault-injection point.
- Enforced by the literal scan (section 5).

## 4. Size budgets and the ratchet

- Keep `size-budget.json` in the repository root, with limits for: tracked files, total lines, product code lines, test code lines, test data files and lines, docs lines, lines per file (300), projects or packages, interfaces, and allowed top-level directories.
- After each milestone, set every budget to actual plus 15%.
- Raising a budget needs the owner's approval in the pull request and a one-line reason in `size-budget.json`.
- Every change states its net line change. A change that grows code says why in one line.

## 5. The size gate

One script, `scripts/size_gate.py`: Python 3, standard library only, under about 100 lines, the same file in every repository whatever the stack. Run it with `python3 scripts/size_gate.py` first in CI and in the pre-commit hook. It must:

1. List files with `git ls-files --cached --others --exclude-standard`; classify each as product, test code, test data, docs, build or generated (lock files count to total size, not code size).
2. Print a table of files and lines per class, and fail (exit 1) when any budget is exceeded.
3. Fail on forbidden paths: versioned copies (`*-v[0-9]*.*`, `*_old.*`, `*.bak`, `*.orig`, `*.py.txt`-style frozen copies), evidence, handoff and ledger directories, and generated indexes.
4. Count interface or abstract declarations in product code and fail above budget.
5. **Literal scan:** collect every identifier and value of 3 or more characters from test data (headers, cells, keys, names, totals, hashes) and fail if any appears in product code, matched on word boundaries. Keep an explicit allow-list for genuine collisions, each with a reason.
6. Fail on product string literals that look like connection strings, absolute paths, IP addresses, 64-character hex hashes or secrets.

## 6. Git is the history

- Edit files in place. Never commit `-v2` copies, frozen copies, recorded evidence, run logs, handoffs, ledgers, status trackers or generated test vectors.
- Record results in the commit message or pull request, not in the tree.
- Use short-lived branches; delete each branch and worktree when it merges.
- Never commit secrets. The pre-commit hook is `.githooks/pre-commit`, a Bash script that runs the size gate and `gitleaks git --pre-commit --staged`; enable it once per clone with `git config core.hooksPath .githooks`. CI runs `gitleaks` too.
- `.gitignore` covers build output, caches, logs, local data and real inputs from the first commit.

## 7. Delete before adding

- Before writing code, look for code to remove or reuse. Remove replaced code in the same change.
- Delete dead code, unused options, unused dependencies and commented-out code; Git keeps them.
- Prefer rewriting a small slice over keeping a large one that has never run end to end.

## 8. Testing

- Test required behaviour, boundaries and realistic failures, weighted by risk. Do not test private implementation details.
- Expected values are literals written by hand. Never compute the expected value with product code.
- Each test run gets fresh, isolated resources: its own database, temporary directory, port and identities. Never reuse a dirty baseline.
- Check prerequisites first and fail fast. Label setup failures `SETUP:`; a setup failure is neither a pass nor a product failure.
- When a test fails, keep the failing case and rerun it unchanged after the fix. If the expectation was wrong, say so in the commit.
- Keep test data small and hand-written; the minimum rows that exercise each rule.
- Integration tests run against the real database engine. Server engines are started by the tests themselves with Testcontainers for the stack's language; SQLite uses a file in a temporary directory. Never an in-memory substitute, a compose file or a CI service container. The same test command runs locally and in CI; Docker is the only prerequisite.
- One test project or package per product unit unless the budget says otherwise.

## 9. Databases

- Schema changes are numbered, forward-only, plain SQL files: `migrations/0001_create_orders.sql`. No migration framework and no ORM migrations.
- Apply them with a small runner in the host language, using only the standard library and the database driver. It records each applied version in a `schema_migrations` table (`version`, `applied_at`) and runs each file and its version row in one transaction. A file whose first line is `-- no-transaction` runs outside a transaction; use it only for statements the engine forbids inside one.
- The runner is a `migrate` subcommand of the application. It connects as the schema-owner identity; the application never migrates at start-up.
- Until the first release, edit migration files in place and recreate the database. After release, never edit an applied file; add a new one.
- Money uses the database's and the language's native exact decimal type; the stack files name it. Never binary floating point, and never a database `money` type.

## 10. Safety: never trade for brevity

- Validate all external input at the boundary; parameterise every query; never build SQL or shell commands from untrusted text.
- Keep a data change and its record of that change in one transaction.
- Never blindly retry an operation whose commit outcome is unknown; check first.
- Check authorisation and target identity before every effect, not once at start-up.
- Least privilege: separate identities for read, write and administration. No shared admin accounts in application code.
- Fail closed: on an unexpected state, stop and report, never guess.
- Use exact types for money and quantities (section 9); use UTC with explicit offsets for time.
- No secrets in code, logs, error messages or test data.

## 11. Dependencies

- Add a dependency only with a one-line reason in the pull request naming what it replaces.
- Commit a lock file and install in locked mode in CI.
- Pin tool versions (SDK, runtime, linter) in the repository.
- Run the stack's vulnerability audit in CI; fail on known high-severity issues.
- Remove a dependency the moment its last use goes.

## 12. Review

- Before merging, run `/simplify`, then `/code-review medium`.
- Use one independent review, with fresh context, for authority, transaction, security or data-format changes. Never two reviewers re-implementing the same thing.
- Reviewers report demonstrated bugs, requirement gaps and material risks with evidence and a fix. Style is the formatter's job.

## 13. CI

- One GitHub Actions workflow, `.github/workflows/ci.yml`, on `ubuntu-latest`, running on pull requests and pushes to the main branch. Steps, fastest first: size gate, `gitleaks`, locked restore, build with warnings as errors, format check, lint, tests (Testcontainers needs no service setup).
- No scheduled jobs, and no extra workflows until a second deployment target exists.
- A green CI run is necessary, not sufficient: the end-to-end test must also pass.

## 14. AI agents

- One agent by default. Use at most 4 in parallel, only on disjoint paths, each with an explicitly assigned model and effort.
- Give each agent a short task: inputs, expected result, forbidden effects, paths it may change. No pasted history.
- No process apparatus: no ledgers, slot files, pipeline tools, route indexes or handoff directories in the repository.
- An agent stops when the task's done conditions are met; it does not add extra improvements, tests or docs.

## 15. Definition of done

- The requested behaviour works end to end, and the test proving it passes in CI.
- Existing behaviour still works; the size gate and every CI step pass.
- No known in-scope critical bug remains; limits and deferrals are written down with triggers.
- Replaced code, branches and worktrees are deleted.

## Anti-patterns seen

Drawn from one repository that grew to 326k lines without ever running end to end, then was rewritten in 4.5k:

- Process files at 95% of the repository: 472 docs files, a 1,875-line ledger and a 1,125-line pipeline tool.
- 168 `llm-routes.json` navigation indexes that needed their own generator, tests and CI.
- Stacked `-v1`…`-v4` SQL files, each altering the previous, needing 8 scripts in order to install.
- Product code loading SQL and schemas from test folders.
- Fixture values in product logic: input byte counts, a SHA-256, a schema size and expected totals.
- 91 interfaces, 62 with no implementation and 21 with exactly one.
- Twin reviewer re-implementations of the same logic instead of one independent review.
- 115 worktrees and 160 branches left in place.
- A message broker, file journal and self-verification layers for a synchronous one-row-at-a-time write.
- A CLI entry point that printed "not available" while CI reported green.
