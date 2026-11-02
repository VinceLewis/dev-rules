# Canonicalise one rule file

Make one rule file prescribe exactly one way to do each thing, following best practice, so Claude gets it right first time.

## Inputs

- Target file: `<file>` (one of @"dev_rules.md" or @"dev_rules_<stack>.md").
- The general rules, @"dev_rules.md", which the stack files must not contradict.

## Task

1. Find every place where the file offers a choice: "X or Y", "either", "for example", "consider", "if you want", "optionally", "or keep", or lists alternative tools, libraries or styles.
2. For each one, decide on the single best-practice option as of today. A third-party package that has become the de facto standard (for example `chi` for Go routing) counts as a candidate alongside the standard library.
3. If you are 90% or more sure, rewrite the rule so it names only that option. Keep it imperative and checkable.
4. If you are less than 90% sure, leave that rule unchanged and report it as an open question (format below).
5. Also fix rules that are vague about the canonical tool, command, file path or version when a single answer is clear (for example "a linter", where the stack has one standard).
6. Remove rules that `dev_rules.md` now covers. Reword rules that contradict it.

## Constraints

- Edit only `<file>`. Do not create other files.
- Keep the existing structure, voice and terseness. Do not grow the file by more than about 15% in lines.
- Keep "when to use X instead" rules only when they are decision rules with a checkable trigger, not menus.
- Do not add new topics beyond what you need to remove a choice.

## Output

- The edited file.
- A short list of the changes: `old choice → chosen option: one-line reason`.
- Open questions, each as: the question; 2 to 4 options, each with a one-line description; your recommended option, with a one-line reason.
