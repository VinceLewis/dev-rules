# Add test-driven development, review and reporting rules

Add the owner's agreed test-driven development, review and reporting rules to the rule files, globally and per stack.

## Inputs

- @"dev_rules.md" and the `dev_rules_*.md` stack files.
- Reference material: @"/home/vince/projects/personal/test_local_ai/AGENTS.md", @"/home/vince/projects/personal/test_local_ai/scenarios.md", @"/home/vince/projects/personal/test_local_ai/tdd-log.md" and @"/home/vince/projects/ai_instructions/dev_instructions.md".

## Decisions already made by the owner

- TDD goes in `dev_rules.md` §8, with no separate test-rules file. Split it out only if the section passes about 60 lines.
- Scenarios go in `docs/scope.md` as `<behaviour>: <input> → <expected>`, with no checkboxes.
- The slice's end-to-end test is written first.
- Each cycle is one scenario: write the test, see it fail on the assertion, write only what that test needs, run the whole suite green, then refactor.
- Red evidence goes in commit messages (`Red:` lines). No TDD log files.
- Tests may not be weakened to get green. No committed skip markers; the size gate checks this.
- Bug fixes start with a reproducing test.
- Cases are chosen with the ISTQB prompts, and repeated cases go in table or parametrised form.
- UI behaviour is testable without the UI. Web UIs get Playwright tests.
- Property or fuzz tests only for code that parses untrusted input: Go native fuzzing, Python Hypothesis, TypeScript fast-check, .NET CsCheck.
- No mutation testing. Coverage percentage is not a completion criterion.
- The size gate fails when a commit changes product code without test code, unless its subject starts with `Refactor:`. It runs over CI's commit range.
- In existing repositories, new code follows the rules. Existing code changes to match only when it is in the change's scope.
- Review (§12):
  1. `/simplify`, then rerun the tests and revert any simplification that changes behaviour or breaks a rule.
  2. `/code-review medium`, or `high` for authorisation, transaction, security or data-format changes. Never `--fix`.
  3. Each confirmed bug gets a failing test, then the fix. Out-of-scope findings are reported, not fixed.
  4. One pass of each. Record the result as a `Review:` line.
  5. No `/security-review`.
  6. Agents without these skills do both passes by hand.
- A new Reporting section, taken from `dev_instructions.md`.

## Constraints

- Do not renumber existing sections; stack files cite them.
- Keep the voice imperative, terse and checkable. Every rule names one way.
- Each stack file gets only its run-one-test command, its table form, and its property or fuzz tool where one applies.

## Output

- The edited files, committed and pushed to `VinceLewis/dev-rules`.
- A short summary of the changes and of any facts that are still unverified.
