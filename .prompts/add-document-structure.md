# Add the document structure

## Inputs

- `dev_rules.md` sections 1 (Scope), 4 (Size budgets), 8 (Testing), 14 (AI agents), 15 (Definition of done) and
  Anti-patterns seen.
- `grep -n 'scope.md\|docs/' *.md`, to find every rule that names a project document.
- The decision, approved by the owner: a project keeps four kinds of document, each answering one question and
  changing at its own speed.
  - `docs/requirements.md`: ranked requirements, with the roadmap (ordered slices, each with a size estimate) last.
  - `docs/scope.md`: the single current truth, with every deferral as `Deferred: <feature>. Trigger: <event>.`
    Budget 300 lines. Rewritten in place when a slice merges.
  - `docs/slice-<n>.md`: a temporary change spec for one slice in progress. Deleted when the slice merges.
  - Nothing else: no layered specs, no frozen copies.

## Task

1. Section 1: replace the two scope bullets with the four-document rule, the slice file written and approved before any
   code, and the merge step (fold into scope.md and the roadmap, delete the slice file, reasons in the commit message).
2. Section 4: add `docs/scope.md` (300 lines) to the budget list.
3. Section 8: write scenarios in `docs/slice-<n>.md`.
4. Section 14: write the contract and file ownership in `docs/slice-<n>.md` before packets start.
5. Section 15: deferrals live in `docs/scope.md`; the slice file is folded in and deleted.
6. Anti-patterns seen: add one bullet on specs layered slice on slice.
7. Check that no other file names scope or slice documents.

## Constraints

- Edit only `dev_rules.md` and this prompt. Do not restructure unrelated sections or repeat rule text across files.
- Keep the voice: short imperative bullets, British English, section cross-references.

## Output

- The diff, committed in one commit (short subject, body listing the changes) and pushed. No force-push, never
  `--no-verify`.
