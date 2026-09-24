# DWS pilot integration — cr-0km.10

2026-09-22. Implementation candidate; independent review and orchestrator
acceptance remain pending. Worktree branch `dws`, unchanged HEAD
`4f3032ccb2e8b796768c913f25be1df7e600bd47`. No commits, branch operations,
worktrees, delegation, or Beads commands were performed.

## Sources and equality

- Package: `27ecc265360a97fe993ce3ae017287191fc66ccb`.
- Lock: `15de351b7415853d4e138f8963d5335b63f03b3b`.
- QMD/latest: `f50238a3b6c615d912b45e702dff062d7dfafc77`.

`git merge-base --is-ancestor` verified package → lock → latest (exit 0
for both edges). None is an ancestor of the current HEAD. Scoped source
history was inspected before importing. The latest tree contains the package
and both suites; its lock source/report equals the lock commit. The only
change to the ten original package files is registration of the `qmd` pytest
marker in `pyproject.toml`.

Both destination directories were absent. Seventeen missing files were
copied with `git show <latest>:<path>` using exclusive file creation. Each
working-file `git hash-object` equals its exact latest source blob:

- `dws/.python-version`, `dws/README.md`, `dws/pyproject.toml`, `dws/uv.lock`;
- `dws/src/dws/{__init__.py,__main__.py,cli.py,py.typed}`;
- `dws/tests/{test_cli.py,test_package.py}`;
- `dws/tests/qualification/{lock_probe.py,test_slot_lock_lifecycle.py,qmd_qualification.py,test_qmd_qualification.py}`;
- [lock report](lock-qualification.md), [QMD report](qmd-qualification.md),
  [QMD manifest](qmd-qualification-manifest.json).

No existing file was replaced. The empty historical `.gitkeep`, historical
`pilot-baseline.json`, and root scripts were excluded. Imported reports and
manifest describe historical runs, not current qualification. Their references
(and README reference) to `scripts/verify-dws-pilot.py` do not provide a current
gate: that script is absent here and its other-checkout baseline was not imported.

Temporary evidence is under `scratchpad/dws/integration/` (ignored, local):
`ancestry.json`, `source-changes.txt`, `import-manifest.json` (per-file source
and working blob IDs), `package-to-latest.diff`, `lock-to-latest.diff` (empty).

## Actual checks

Package commands ran from `dws/`, with `UV_FROZEN` removed and
`UV_CACHE_DIR` set to this worktree's `scratchpad/dws/integration/uv-cache`.
`checks.json` records argv, cwd, exit codes and log paths. Log names below
are relative to that evidence directory.

| Command | Actual result | Log |
|---|---|---|
| `uv sync --locked` (sandbox) | Exit 1, dependency download blocked by DNS | `sync.log` |
| `uv sync --locked` (approved network execution) | Exit 0, locked environment installed | `sync-host.log` |
| `uv run --locked dws --help` | Exit 0; scaffold only | `help.log` |
| `uv run --locked pytest -q -s` | Exit 1: 16 passed, 4 QMD setup errors; no skips | `pytest.log` |
| `uv run --locked ruff check .` | Exit 0 | `ruff.log` |
| `uv run --locked ruff format --check .` | Exit 0, 10 files formatted | `format.log` |
| `uv run --locked mypy --strict src/dws` | Exit 0, 3 source files | `mypy.log` |
| `uv build --wheel` | Exit 0, `dist/dws-0.0.1-py3-none-any.whl` | `wheel.log` |
| `uv run --locked python -m compileall -q src tests` | Exit 0 | `compile.log` |
| Root `.venv/bin/python -m pytest --collect-only -q` | Exit 0: 1310/1315 collected, 5 deselected | `root-collection.log` |

The 16 passing tests include all six real-process lock probes: slot capacity,
release, filesystem observation, inherited descriptor lifetime, and the
parent-only negative control. Observed filesystem: ext4, mount `/tmp`.
This is local Python-child evidence, not a deployment-volume or QMD-child pass.

QMD is absent from PATH and no candidate override was supplied. All four QMD
probes fail explicitly at setup. Separately,
`bwrap --unshare-net --ro-bind / / -- true` exits 1 because creation of its
`NETLINK_ROUTE` socket is denied (`bwrap.log`). No isolation was bypassed,
test weakened, QMD candidate installed, or QMD qualification pass claimed.
`runtime-availability.json` and `platform.log` record the available facilities.

## Preservation and remaining work

`preserved-before.json` and `final-equality.json` cover 246 existing protected
and root source/tooling/test files. Root files and the pre-existing goal doc
remain byte-identical; the already-dirty `.beads/issues.jsonl` changed during
this worker's run, consistent with concurrent work. This worker never wrote
it and did not revert it. All 17 imported blobs still match their source.
Root collection succeeded; no before-run collection snapshot was taken, so
collection invariance rests on unchanged root files, not a paired run.

Final structural validation: JSON parsing, imported-file whitespace checks,
scoped `git diff --check`, and Git status inspection passed. The final global
`git diff --check` also passed: `global-diff-check.log` records exit 0 with no
diagnostics.
Full interpreter execution is
outside this package-only change. No product capability or P1 completion is
claimed. Remaining implementation follow-up: set up the pinned QMD candidate
with working network-denied execution, then qualify QMD child ownership and
the intended container volume for G-02/G-03. This is implementation work, not
a request for the owner to arrange the setup manually.
