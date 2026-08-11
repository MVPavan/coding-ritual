Direct answer: **KEEP the current copy-on-adopt + manifest three-way update as the default architecture**, but fix several implementation/documentation smells and start a **non-default hybrid track** for optional/high-churn reusable capabilities.

The prior hard constraint “Codex CLI has no plugin system” is now **verified false**: local `codex-cli 0.142.2` has `codex plugin`, and OpenAI docs now describe Codex plugins for skills, apps, MCP servers, and hooks. But that does **not** make plugin-native adoption strictly better, because Claude and Codex plugins still require per-user install/trust, while the core requirement here is: a collaborator gets the working harness by `git clone`. Current copy-on-adopt is still the only architecture that fully satisfies that.

**What A Good Answer Must Cover**
The deciding question is not “which model updates reusable files most elegantly?” It is “which model simultaneously preserves clone-only collaborator onboarding, repo-owned customization, non-destructive updates, Codex/Claude parity, and trust boundaries?” On those constraints, copy-on-adopt still wins; hybrid is the best future pressure valve.

**Observed Facts**
- Current `/adopt` copies inert `template/` payload into `.claude/`, `.codex/`, `.beads/`, `CLAUDE.md`, and `AGENTS.md`; `/update` re-runs the deterministic installer with base/local/new merge semantics. See [README.md](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/README.md:43) and [install-harness.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:39).
- The implemented update logic preserves local edits, writes `<file>.template-new` when local and upstream both changed, and retires removed upstream files only when locally unmodified. See [install-harness.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:57) and [install-harness.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:149).
- The template subset invariant is real: `build-template.sh` excludes project overlays and curation-only tooling via `template-exclude.txt`, genericizes, leak-checks, and emits `harness-manifest.txt`. See [build-template.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:51), [template-exclude.txt](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/template-exclude.txt:16), and [build-template.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:162).
- Claude Code plugins are good for reusable, versioned distribution, but Anthropic explicitly says project-enabled external plugins do **not** install for other people and every path asks users to install/trust before running. Source: https://code.claude.com/docs/en/settings and https://code.claude.com/docs/en/plugins.
- Codex plugins now exist, but OpenAI’s build docs list plugin components as skills, apps/connectors, MCP servers, and hooks; AGENTS.md/rules/subagents still appear as repo/config surfaces. Source: https://developers.openai.com/codex/plugins and https://developers.openai.com/codex/plugins/build.
- Git submodules do not satisfy clone-only onboarding: a normal clone leaves submodule contents empty until extra commands are run. Source: https://git-scm.com/book/en/v2/Git-Tools-Submodules.
- Symlink/central-store designs remain weak on Windows/container/trust boundaries; Windows symlink creation and semantics are not a clean universal baseline. Source: https://learn.microsoft.com/en-us/windows/win32/fileio/symbolic-links and https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createsymboliclinka.

**Ranked Recommendation**
1. **KEEP A: copy-on-adopt + three-way update.** Best fit for clone-only collaboration, repo ownership, arbitrary target repos, and non-destructive local customization. The update mechanism directly solves the old silent-overwrite defect.
2. **Pursue D as a staged option, not a replacement.** Create dual Claude/Codex plugin packaging for optional or high-churn reusable capabilities, but keep a copied bootstrap/core until plugin install/trust is acceptable for every collaborator.
3. **Reject B/C/E/F as default architectures.** They optimize deduplication or central updates while breaking clone-only onboarding, cross-platform reliability, or local ownership.

**Comparison Table**
| Architecture | Verdict | Where It Works | Where It Breaks |
|---|---|---|---|
| A. Copy + three-way | **Keep** | Best clone experience; repo owns files; real `.codex`; local edits protected; template subset implemented | Manual `/update`; dual-tree drift; Bash portability; docs/tests stale |
| B. Plugin-native/reference | Reject as default | Better central updates for Claude, now partly Codex | Per-user install/trust; weaker repo ownership; Codex plugin surface still incomplete for full harness; asymmetric if Claude-only |
| C. Template-as-plugin | Reject if runtime plugin; current if installer payload | Fine as “plugin ships installer payload” | If not copied, breaks `AGENTS.md`/root files/clone-only; if copied, it is just A |
| D. Hybrid | Best future path | Reduces copied high-churn skills/hooks; marketplace updates; clearer optional capabilities | Still needs per-user plugin install/trust; migration cost; needs dual Claude/Codex plugin packaging and version gates |
| E. Dependency/submodule/subtree/package | Reject | Version pinning and provenance are familiar | Submodules require extra clone/update commands; subtree/package reintroduces merge/install friction; customization awkward |
| F. Symlink/central store | Strong reject | Minimal disk duplication | Breaks clone/container portability, Windows assumptions, trust review, and repo ownership |

**Current Smells To Fix**
- `check-sync.sh` currently fails before reporting drift because `sync-manifest.txt` references `skills/ak-guide/SKILL.MD`, but the payload has `SKILL.md`. See [sync-manifest.txt](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/sync-manifest.txt:45).
- `build-template.sh` treats sync drift as advisory only, so a broken sync checker can slip through. Make malformed manifest paths a hard failure.
- Plugin docs are stale after the marketplace restructure: `README.md` and `plugin.json` still imply bundled `codex-adapter`, while the root marketplace now lists `mvp-plugin`, `code-intel`, and `codex-adapter` as siblings. See [docs/usage/mvp-plugin.md](/data/codes/coding-ritual/docs/usage/mvp-plugin.md:298), [plugin.json](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/.claude-plugin/plugin.json:4), and [marketplace.json](/data/codes/coding-ritual/mvp-harness/.claude-plugin/marketplace.json:12).
- Tests cover local-edit preservation, but not the highest-risk update cases: both-changed `.template-new`, orphan retire, locally modified retired file, and the broken sync-manifest path. See [run-tests.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/test/run-tests.sh:59).

**Verification**
Ran `bash -n` on the four mvp-plugin scripts: pass. Parsed root marketplace and mvp-plugin `plugin.json`: pass. Ran `check-sync.sh check`: failed with missing `SKILL.MD`, which is a real current defect. `git status` shows pre-existing uncommitted files only; I made no edits.

**Open Questions**
- Is “no per-machine install” absolute, or is “first-run prompted plugin trust” acceptable later? That single policy choice determines when D can replace part of A.
- Should Codex plugin support be version-gated now, or only after the harness supports both old no-plugin Codex and new plugin Codex?
- Which copied skills are truly universal core versus optional plugins? That should be decided by measured use, not by a desire to shrink the template.


