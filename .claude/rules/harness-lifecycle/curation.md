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
- **Never edit the plugin's build output by hand.** `mvp-harness/plugins/mvp-plugin/`
  `skills/`, `agents/`, and `template/` are built from this repo by
  `/harness-publish` (`scripts/publish-plugin.sh`). Change the source here, publish,
  commit the plugin repo, then bump the submodule pointer.
- **Curation tooling stays root-only.** Name lifecycle skills/hooks `harness-*`
  and put lifecycle rules under `rules/harness-lifecycle/`; `publish-manifest.txt`
  (`exclude`) and `template-exclude.txt` keep them out of the plugin. Drafts live
  under `skills/in-progress/` (not loaded, not shipped). The plugin's shipped set
  must stay a strict **subset** of the root harness.
- **Default to reject/defer.** Borrow the smallest durable pattern; do not import
  whole catalogs or workflows.
