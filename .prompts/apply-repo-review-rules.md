# Apply the rules accepted from a repository review

Turn the owner-approved proposals from a repository review (see @".prompts/mine-repo-for-rules.md") into rule text. Write the reviewed repository's own problems to a findings file in that repository for later work.

## Inputs

- The approved proposals and decisions from the review conversation.
- @"dev_rules.md" and the `dev_rules_*.md` stack files.

## Task

1. Write `<repo>/claude-findings.md`. List the repository's problems in priority order, each with its evidence (`path:line`), its effect and the fix. Mark the steps only the owner can do, such as rotating credentials or server changes. Fix nothing in the repository.
2. Apply every approved proposal to the rule files. Create the new stack files the owner approved and add them to the index in `dev_rules.md`.
3. Apply the owner's caveats. For the giggle review:
   - **Nothing hard-coded.** Operational values (timeouts, limits, rates, retention, log level, header policy) come from one JSON settings file named by `--config`, with every key required and no defaults in code. Secrets stay in environment variables.
   - **Diagnosability.** Replace "no debug mode" with diagnostics as a product feature:
     - structured logs and request IDs;
     - `log_level` as a setting;
     - health checks and client error reports.

     Test-only code paths stay banned.

## Constraints

- Never write secret values. Name the file and the kind of secret only.
- Keep the voice imperative, terse and checkable, with one way per rule. Keep `dev_rules.md` under 300 lines.
- Do not renumber sections.

## Output

- The findings file, and the edited and new rule files, committed and pushed to `VinceLewis/dev-rules`. Do not commit the reviewed repository.
- A summary of what changed, and the answer to any question the owner asked.
