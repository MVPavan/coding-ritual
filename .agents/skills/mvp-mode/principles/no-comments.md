# No comments

A comment that narrates what the code does goes; the code should say it.

- Keep a comment only when it is one of these:
  - a license or legal header;
  - behaviour forced by an external dependency, platform, vendor or protocol
    we cannot reshape; surprising behaviour in code we control does not
    qualify;
  - a `prettier-ignore` or other formatter directive, or a lint or type
    suppression whose rule is faulty or only about style;
  - a doc comment that defines a public API contract;
  - an issue or RFC link that explains a constraint the code cannot express.
- A comment that forbids removing or rewording something, or says to consult
  someone before changing it, is a constraint comment: a class of its own,
  neither narration nor a keep by default.
- A suppression that silences a check bearing on correctness or safety is a
  finding to remove, never a keep.
- A decision on a comment ends in one state. The exact exception, proven in
  scope: a settled keep, kept or brought back, with no flag. Shown unneeded or
  wrong: it goes. A real constraint we control: the enforcement offer. Still
  unsure: keep it, bringing it back if already deleted, and flag it; no proof
  is needed for that. The `/no-comments` sweep is what makes the enforcement
  offer.
- Never delete a comment one of the exceptions above protects.
- When unsure whether a comment should go, keep it, bringing it back if already
  deleted, and flag it for a person. A comment shown to be wrong can still go.
