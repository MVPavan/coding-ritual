# Reference-Harness Curation — Guardrails

Rules for the reference-harness lifecycle (detect → evaluate → route → sync).
Tooling: `harness_lifecycle/` (`scan.py`, `gap.py`) + the `/harness-status` and
`/harness-scan` commands and the `harness-evaluate` skill.

- **Reference harnesses are read-only inspiration.** Never edit anything under
  `reference_harnesses/`. Scans and status checks may `git fetch`, but must **never**
  move a pinned commit (`git submodule update`, checkout) without an explicit,
  separate request.
- **No adoption without a ledger entry.** Every decision (adopt / reject / defer)
  goes in `harness_lifecycle/ledger.json` via `gap.py ledger add`, so the gap report
  stops re-surfacing it.
- **Never edit the generated template by hand.** `mvp-harness/.../template/` is built
  from the root `.claude`/`.codex`. Change the source, run `check-sync.sh` then
  `build-template.sh`, then bump the submodule pointer.
- **Curation tooling stays root-only.** Name lifecycle skills/commands/hooks
  `harness-*` and put lifecycle rules under `rules/harness-lifecycle/`;
  `template-exclude.txt` keeps them out of adopted repos. The template must stay a
  strict **subset** of the root harness.
- **Default to reject/defer.** Borrow the smallest durable pattern; do not import
  whole catalogs or workflows.
