# Code Intelligence (code-intel plugin)

**Recommendation: not needed for this repo.** Report-only.

- **Size / shape:** ~148 tracked files (excluding submodules), overwhelmingly
  Markdown (~267 incl. submodule-adjacent) and Bash, with only scattered Python
  and Node tooling. This is well under the "large, navigation-heavy codebase"
  threshold the plugin targets.
- **Primary language / LSP:** none dominant. No first-party application package
  for an LSP to index meaningfully; symbol-graph navigation buys little over
  plain grep/Glob here.
- **Index state:** not indexed; `.serena/` and `.codebase-memory/` are gitignored
  but absent.

Note: the `code-intel` plugin's *source* lives in this repo
(`my_harness/code-intel/`), but that is the artifact being developed, not a
reason to run it against this repo. Revisit only if substantial first-party
source code in a single LSP language lands here.
