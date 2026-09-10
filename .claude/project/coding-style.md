# Python Conventions

Read before writing or changing Python code. These are project choices, not a
general style checklist.

## Formatting, linting, and types

- Use Ruff: `uv run ruff format <paths>` and `uv run ruff check <paths>`.
  Follow repository configuration; keep formatting scoped to the requested work.
- Use strict mypy and explicit function signatures. Run the applicable commands
  in `.claude/project/verification.md`, including its repository-specific options.
- `uv run ty check workflow_interpreter/` is optional feedback, not a replacement
  gate; see `docs/research/python-tooling/ty-vs-mypy.md` before changing checkers.

## Data modeling

- Prefer Pydantic v2 `BaseModel` over dataclasses or untyped dictionaries for new
  structured domain data, configuration, and external contracts. Ordinary
  collections can remain built-ins; do not rewrite existing models incidentally.
- Default data models to `ConfigDict(frozen=True)`; use mutable models when their
  lifecycle requires mutation. For closed input schemas, use `extra="forbid"`.
- Use Pydantic `Field(default_factory=...)` for per-instance collection defaults.
  Keep arbitrary framework objects out of serialized contracts.
- Preserve the component's configuration format; Pydantic validation does not
  require introducing YAML or `pydantic-settings`.

## Package management

- Use uv: `uv sync` for the environment and `uv run` for Python tools/scripts.
- Manage dependencies with `uv add` / `uv remove` (`--dev` for development tools).
  Keep `pyproject.toml` and `uv.lock` consistent; do not use ad hoc pip installs
  as a substitute for declaring project dependencies.
