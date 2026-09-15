# DWS

DWS is a **scaffold**. This directory is an independent Python distribution
that owns its own manifest, lockfile, tests and dev tooling, separate from the
`coding-ritual` project at the repository root.

What exists today is the boundary and the tooling around it: an installable
package (`src/dws`) and a `dws` console entry point that reports what the
distribution is. Nothing from the DWS design — storage, acquisition,
retrieval, discovery, runtime controls, MCP — is implemented, and the CLI
exposes no command that would imply otherwise. Capabilities land with the
stages that build them; see `docs/workstreams/dws/roadmap.md`.

Runtime code is standard library only, on Python 3.13 (pinned in
`.python-version`); third-party dependencies are dev tools.

## Local setup and checks

Run every command from this `dws/` directory. Root tooling is not involved and
must not be changed to accommodate this package.

```sh
uv sync --locked                    # create/refresh the environment from uv.lock
uv run --locked dws --help          # the installed console script
uv run --locked pytest -q           # tests
uv run --locked ruff check .        # lint
uv run --locked ruff format --check .   # formatting
uv run --locked mypy --strict src/dws   # types
uv build --wheel                    # build a wheel into dist/
```

After changing a dependency in `pyproject.toml`, re-lock with `uv lock` and
commit the updated `uv.lock`.

The pilot's acceptance check runs all of the above, plus a check that the root
project's sources and test collection are untouched. From the **repository
root**:

```sh
python3 scripts/verify-dws-pilot.py
```
