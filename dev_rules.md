# Development rules

Goal: simple, short, working code from the first commit. Every rule is imperative and checkable; where a machine can check it, CI does.

Every rule names one way to do a thing. Never offer or pick an alternative. When a choice comes up that no rule covers, ask the owner, then add the answer to these files.

## Adopting these rules

1. Copy `dev_rules.md` and the stack files you use into `docs/rules/`.
2. Import them from `CLAUDE.md`, one line each, for example: `@docs/rules/dev_rules.md` and `@docs/rules/dev_rules_dotnet.md`.
3. Add the size gate (section 5), the pre-commit hook (section 6) and the CI workflow (section 13) in the first commit, before any feature code.
4. Delete the stack files you do not use. Project-specific rules go in `CLAUDE.md`, never in these files.
5. In an existing repository, new code follows these rules. Bring existing code into line only when the change's scope includes it, never as a side effect. Record existing breaches of the file and line-width caps as `legacy` entries (section 4) in the adoption commit.

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
| `dev_rules_web.md` | an HTTP server or a browser UI |
| `dev_rules_deploy.md` | a service deployed to a Linux server |

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
- No feature option or mode without a user who sets it to two different values. Operational values are settings (section 3), not options.
- Use the standard library and the platform's built-in features. Where a stack file names a third-party package as the standard, use that package; never write your own or choose a different one.
- Prefer one longer obvious function over five short indirect ones; split on reuse or the file limit, not on taste.
- Synchronous and in-process first. Queues, brokers, caches and background workers need a measured reason.

## 3. No hard-coding

- Product code must not contain names, values, counts, totals, hashes, paths, URLs or connection strings that belong to data, nor operational values: timeouts, sizes, limits, rates, retention, addresses, log level or header policy.
- Data comes from input. Per-run inputs come from command-line arguments. Operational values come from one JSON settings file named by `--config`: snake_case keys, units in the key name (`read_timeout_seconds`, `max_body_bytes`), every key required, unknown keys rejected, validated at start-up, no defaults in code. JSON because every stack parses it with its standard library. Secrets and connection strings come from environment variables only, never the settings file.
- The production settings file lives in the repository (`dev_rules_deploy.md`); each test writes its own.
- Hard-coded data is allowed only in tests and test data.
- Product code never reads from test folders and never branches on "test mode". No test-only endpoints, commands or code paths in the product build, even behind a flag or variable: tests set up and clean up through the public API or their own database. Allow at most one named, internal fault-injection point. Diagnostics (section 10) are product features, not test code.
- Enforced by the literal scan (section 5).

## 4. Size budgets and the ratchet

- Keep `size-budget.json` in the repository root, with limits for: tracked files, total lines, product code lines, test code lines, test data files and lines, docs lines, lines per file (300), line width (120 characters), projects or packages, interfaces, and allowed top-level directories.
- After each milestone, set every budget to actual plus 15%.
- No source file exceeds 500 lines, so an agent can read and edit the whole file in one pass. The lines-per-file budget is never ratcheted or raised past 500; split the file by responsibility instead. The only exception is a `legacy` entry (next rule), which can only fall. Source files are product code, test code, scripts and CI files; docs, data, test data, generated and lock files are exempt.
- In an existing repository, list each source file over 500 lines or with lines over the width budget under `legacy` in `size-budget.json`: its path, line count and number of wide lines. Each figure may only fall, with no headroom: the gate fails when a file exceeds its figures or a figure is above the actual value, so it is lowered in the change that earned it. Remove the entry once the file complies. An entry added after the adoption commit is a budget raise. The 15% headroom applies only to the other budgets.
- A slice's size estimate is its budget: set caps to actual plus the estimate, not a round number. A slice that grows past its estimate says why in one line, even when it is under the cap.
- Budgets limit bloat, not readability. One statement per line. Near a cap, delete duplication or ask to raise the budget; never compress to fit: no joined statements, dense one-liners, packed expressions or shortened names.
- Raising a budget needs the owner's approval in the pull request and a one-line reason in `size-budget.json`.
- Every change states its net line change. A change that grows code says why in one line.

## 5. The size gate

One script, `scripts/size_gate.py`: Python 3.12 or later, standard library only, under about 200 lines, the same file in every repository whatever the stack. Run it with `python3 scripts/size_gate.py` first in CI and in the pre-commit hook. It must:

1. List files with `git ls-files --cached --others --exclude-standard`; classify each as product, test code, test data, docs, build or generated (lock files count to total size, not code size).
2. Print a table of files and lines per class, and fail (exit 1) when any budget is exceeded.
3. Fail on forbidden paths: versioned copies (`*-v[0-9]*.*`, `*_old.*`, `*.bak`, `*.orig`, `*.py.txt`-style frozen copies), evidence, handoff and ledger directories, generated indexes, and files gitleaks cannot inspect: binaries (`*.exe`, `*.dll`, `*.so`), office documents (`*.docx`, `*.xlsx`, `*.pdf`), database dumps and backups (`*.dump`, `*.backup`, `*.bak`, `*backup*.sql`).
4. Count interface or abstract declarations in product code and fail above budget.
5. **Literal scan:** collect every identifier and value of 3 or more characters from test data (headers, cells, keys, names, totals, hashes) and fail if any appears in product code, matched on word boundaries. Keep an explicit allow-list for genuine collisions, each with a reason.
6. Fail on product string literals that look like connection strings, absolute paths, IP addresses, 64-character hex hashes or secrets.
7. Fail on skip and focus markers in test code: `t.Skip`, `Skip =`, `Assert.Skip`, `pytest.mark.skip`, `pytest.skip(`, `pytest.mark.xfail`, `.skip(`, `.only(`, `.todo(` and a bats `skip` line.
8. With `--commits <base>..HEAD`, fail on each commit in the range that changes product code but no test code, unless its subject starts with `Refactor:`. CI passes the range (section 13); the pre-commit hook does not.
9. Fail on any line of code or CI file wider than the line-width budget, so line budgets cannot be met by widening lines. JSON and XML data files, Markdown prose and test data are exempt. A `legacy` file fails when its wide lines exceed its recorded number.
10. Fail on any source file over 500 lines (section 4), whatever the other budgets say. A `legacy` file fails when it exceeds its recorded line count.
11. Fail on any `legacy` figure above the file's actual value, and on an entry for a file that complies or no longer exists.

The gate's test is `scripts/size_gate_test.py`: standard-library `unittest`, run with `python3 scripts/size_gate_test.py`, the same file in every repository. For each check above it builds a temporary Git repository with one seeded breach and asserts exit 1; a clean repository exits 0. A check that has never been seen to fail proves nothing.

## 6. Git is the history

- Edit files in place. Never commit `-v2` copies, frozen copies, recorded evidence, run logs, handoffs, ledgers, status trackers or generated test vectors.
- Record results in the commit message or pull request, not in the tree.
- Use short-lived branches; delete each branch and worktree when it merges.
- Never commit secrets. The pre-commit hook is `.githooks/pre-commit`, a Bash script that runs the size gate and `gitleaks git --pre-commit --staged`; enable it once per clone with `git config core.hooksPath .githooks`. CI runs `gitleaks` too.
- `.gitignore` covers build output, caches, logs, local data and real inputs from the first commit.

## 7. Delete before adding

- Before writing code, look for code to remove or reuse. Remove replaced code in the same change.
- Make the smallest coherent change. Do not refactor working code outside the change's scope.
- Delete dead code, unused options, unused dependencies and commented-out code; Git keeps them.
- Prefer rewriting a small slice over keeping a large one that has never run end to end.

## 8. Testing

### Test-driven cycle

- Before any code, write each slice's scenarios in `docs/scope.md`, one per line: `<behaviour>: <input> → <expected>`. No checkboxes; a scenario is done when its test passes.
- Write the slice's end-to-end test (section 1) first. It stays red while the cycles below build the code under it.
- Take one scenario at a time:
  1. Write its test, or add its row to the existing table.
  2. Run only that test and see it fail on the assertion, for the expected reason. If it does not compile, add a stub that compiles and run it again.
  3. Write only the code that test needs. Never implement a later scenario early.
  4. Run the whole suite and see it pass.
  5. Refactor while the suite stays green.
- Keep a new test that passes on its first run only if it covers a distinct input class or boundary, and say `No red: <test>, already covered by <code>` in the commit. Otherwise delete it.
- Quote each red in the commit message: `Red: <test>: <failure line>`. No TDD log files.
- A bug fix starts with a test that reproduces the bug and fails.
- Never change an expected value, delete a test or skip one to get green without a one-line reason in the commit message. Never commit a skip or focus marker (section 5).

### Choosing and writing tests

- Test required behaviour, weighted by risk, never private implementation details. Choose cases with these prompts:
  - valid and invalid input classes, including empty input where the interface allows it;
  - values at and either side of each boundary;
  - each combination of conditions with a distinct outcome;
  - each state change, including recovery after an error.
- Put cases that differ only in data in one table-driven or parametrised test, in the form the stack file names.
- Expected values are literals written by hand. Never compute the expected value with product code, and never check a schema against the file that built it.
- Test setup imports product definitions (schemas, routes, constants); never copies them.
- Never assert a known bug as correct behaviour. Record it in `docs/scope.md` as a deferral with a trigger; its failing test is written when it is fixed.
- Code that parses untrusted input (text, files, network messages) also gets a property or fuzz test with the stack file's named tool. Assert invariants (never crashes, rejects with the typed error, round-trips), never a re-implementation of the logic.
- Coverage percentage is not a completion criterion. No mutation testing.
- Keep behaviour in code that tests can drive without the UI, and keep the UI layer thin. A web UI gets one Playwright test per user flow.
- Each test run gets fresh, isolated resources: its own database, temporary directory, port and identities. Never reuse a dirty baseline or a warm stand.
- Every UI and journey test creates its own user and data through the public API and removes them in its own cleanup; no shared seeded users.
- A gate passes only on a test command's exit status, never on report files, timestamps or hand-typed counts.
- Check prerequisites first and fail fast. Every check, including the size gate, the pre-commit hook and each CI step, ends as pass, fail or `SETUP:`, meaning it could not run. `SETUP:` is neither a pass nor a product failure: it exits non-zero and is never green.
- Keep test data small and hand-written; the minimum rows that exercise each rule.
- Integration tests run against the real database engine. Server engines, and every other service the tests need (for example an auth server), are started by the tests themselves with Testcontainers for the stack's language, on one network per run; SQLite uses a file in a temporary directory. Start one container per test process; give every test its own database, built by the `migrate` runner. Never an in-memory substitute, a compose file or a CI service container. The same test command runs locally and in CI; Docker is the only prerequisite.
- One test project or package per product unit unless the budget says otherwise.

## 9. Databases

- A server database is PostgreSQL; use SQL Server only when the organisation already runs it. Use SQLite only as `dev_rules_sqlite.md` allows.
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
- Every request that names a resource checks, in the same query, that the caller may access it; answer 404 when not. A missing or commented-out authorisation check is a bug: stop and report it, never keep it as existing behaviour.
- Never treat an unverified email address as identity.
- Verify an inbound webhook's signature with its shared secret before parsing it; reject unsigned calls.
- Error responses carry fixed messages and a request ID, never internal error text.
- Fail closed: on an unexpected state, stop and report, never guess.
- Use exact types for money and quantities (section 9); use UTC with explicit offsets for time.
- No secrets in code, logs, error messages or test data.

### Logging and diagnostics

Diagnose live problems from logs and request IDs, never from a debug mode.

- Log one JSON object per line to stdout: time, level, message, request ID and the event's fields. Never log bodies, headers, query strings, tokens, secrets or personal data, at any level.
- Every request gets an ID, logged on every line it causes and returned in the `X-Request-ID` response header and in every error response, so a user's report leads to its log lines.
- Log each unexpected error once, at the boundary that handles it, with its wrapped cause chain. Errors always log, whatever the level.
- `log_level` is a setting: `info` in production. Raise it to `debug` only while diagnosing, then lower it; debug lines obey the same rules.
- No debug mode that changes behaviour, adds endpoints or loads tools such as in-browser consoles.
- To fix a live problem: find its lines by request ID, reproduce it as a failing test (section 8), then fix it.

## 11. Dependencies

- Add a dependency only with a one-line reason in the pull request naming what it replaces.
- Commit a lock file and install in locked mode in CI.
- Pin tool versions (SDK, runtime, linter) in the repository.
- Run the stack's vulnerability audit in CI; fail on known high-severity issues.
- Remove a dependency the moment its last use goes.

## 12. Review

The agent that made the change runs the review before it pushes, once the change is complete and its tests pass.

1. Run `/simplify`, then rerun the whole suite. Revert any simplification that changes behaviour or breaks these rules; these rules win over the skill. Also revert any that saves lines by making code harder to read (section 4).
2. Run `/code-review medium` with no target, which reviews the unpushed commits and uncommitted changes. Use `/code-review high` when the change touches authorisation, transactions, security or a data format. Never `--fix`, and no second reviewer.
3. For each confirmed bug, write a failing test, then fix it (section 8). Report findings outside the change's scope; do not fix them.
4. One pass of each. Rerun `/code-review` only after fixing authorisation or security code.
5. Record the result in the last commit message or the pull request: `Review: <level>, <n> found, <n> fixed (<tests>)`.

An agent without these skills does the same two passes by hand: a simplification pass, then a bug review of the diff. Reviews report demonstrated bugs, requirement gaps and material risks with evidence; style is the formatter's job.

## 13. CI

- CI builds from the repository alone: every build input is tracked or pinned. Never replace CI with a local hook.
- One GitHub Actions workflow, `.github/workflows/ci.yml`, on `ubuntu-latest`, running on pull requests and pushes to the main branch. Check out with `fetch-depth: 0` and run the size gate with `--commits` over the pull request's commits or the pushed range. Steps, fastest first: size gate test, size gate, `gitleaks`, locked restore, build with warnings as errors, format check, lint, tests (Testcontainers needs no service setup).
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
- The commits carry their `Red:` lines and the `Review:` line (sections 8 and 12).
- Replaced code, branches and worktrees are deleted.

## 16. Reporting

- Write reports, commit messages and agent-to-agent messages in plain British English. Speak as the person doing the work: "I found a bug: the total ignores refunds", not "the owner identified a reconciliation gap".
- Prefer ordinary words: bug, test, fix, change, finished. Describe the observed problem, its effect, the fix and the test result.
- Keep progress updates short, as Done / Found / Next; omit empty parts. Raise only real blockers and decisions.
- Never claim success without evidence. Say which tests ran, and which did not and why.

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
- In the 4.5k rewrite, line budgets met by cramming: 278 lines over 120 characters, the widest 292, and statements joined on one line, until the size gate also limited line width.

From one live production app:

- Any logged-in user could read and change any band's data: a membership check commented out and kept "byte-for-byte" through a data-layer rewrite.
- Every request body logged, passwords included, with a debug flag left on in production.
- Deployment over plain FTP to a directory whose scripts root then ran.
- Database dumps with password hashes, and a passwords document, committed to Git.
- CI dropped because a build input was untracked, replaced by a pre-push hook that checked report timestamps, not results.
- 41 gate JSON files with hand-typed counts no script read, and 52 process documents in `tests/`.
- The schema in four places that had drifted apart, checked by a test against the same file that built it.
