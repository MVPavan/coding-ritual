# Invariants

Hard constraints derived from repo reality. Violating any of these is a defect.

1. **Repo-relative paths only.** No machine-local absolute paths in any committed
   file (docs, prompts, rules, scripts, plugin manifests).
2. **Reference repos stay external.** They live as git submodules under
   `reference_harnesses/`; never copy their contents into the local harness, and
   never edit submodule internals except to bump the tracked commit pointer.
3. **Valid manifests.** Every `plugin.json` and `marketplace.json` must remain
   parseable JSON.
4. **No scratchpad commits.** `scratchpad/` is gitignored throwaway.
5. **Beads sync remote = the repo's own git remote**
   (`git+https://github.com/MVPavan/coding-ritual.git`).
6. **Borrow minimally.** Only the smallest durable pattern that improves the
   harness is pulled from a reference repo (harness design principle).
7. **Explicit staging.** No `git add .` / `-A`, no `--no-verify`, force-push,
   `reset --hard`, `clean`, or `restore` without explicit approval.

Checkable subset (see `verification.md`): manifests parse, changed `.sh` pass
`bash -n`, changed `.py` pass `py_compile`, no machine-local paths introduced.
