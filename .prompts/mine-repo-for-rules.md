# Mine a real repository for best practices to add to the rules

Review an existing repository for practices, good or bad, that the rule files do not yet cover. Propose candidate rules for the owner to review. Edit nothing.

## Inputs

- Target repository: `<repo>` (for giggle: @"/home/vince/projects/personal/giggle-new" for the source, and @"/home/vince/projects/personal/giggle-prod" for the deployed server directory).
- The current rules: @"dev_rules.md" and the `dev_rules_*.md` stack files.

## Task

1. Split the repository into disjoint areas, one agent each, at most 4 (`dev_rules.md` section 14). For giggle:
   - A: the Go server — HTTP security, auth, logging, errors, config;
   - B: tests — Go, Jest and UI/journey tests, gates and the test runner;
   - C: front end, deployment and database.
2. In each area, find:
   - good practices worth making rules;
   - bad practices worth an anti-pattern entry or a rule against them;
   - places where the current rules would be wrong or unworkable for this repository.
3. Drop anything the rules already cover. Note where the repository contradicts a rule.
4. Report live security problems separately from the rule proposals.

## Constraints

- Read-only: no edits, no commands with side effects, no network calls.
- Never print secret values from `.env` files, private keys, credentials documents, `.docx` password files, database backups or logs. Name the file and the kind of secret only.
- Skip third-party code: `node_modules/`, `gotrue-master/`, minified vendor files.
- Every proposal cites evidence as `path:line`.

## Output

- Candidate rules, grouped by target file (`dev_rules.md` or a stack file, or a new stack file if one is needed). Each candidate gives:
  - the rule text, imperative and naming one way;
  - its evidence;
  - whether it is a good practice to adopt or a bad practice to forbid;
  - confidence (≥90% or below, with options when below).
- Live security problems, with severity and evidence.
- A list of what each agent read.
