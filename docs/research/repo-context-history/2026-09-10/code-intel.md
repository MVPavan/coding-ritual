# Code Intelligence (code-intel plugin)

**Historical assessment from the adoption-era repository.** Its size and
language assumptions below predate `workflow_interpreter/` and `tests/`; they
do not establish a current recommendation or index state. Consult this only
when reassessing code-intelligence tooling, using current repository evidence.

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
(`mvp-harness/plugins/code-intel/`), but that is the artifact being developed, not a
reason to run it against this repo. Revisit only if substantial first-party
source code in a single LSP language lands here.
