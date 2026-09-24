# Python Conventions

Read before writing or changing Python code. These are project choices, not a
general style checklist.

## Formatting, linting, and types

- Use Ruff: `uv run ruff format <paths>` and `uv run ruff check <paths>`.
  Follow repository configuration; keep formatting scoped to the requested work.
- Use strict mypy and explicit function signatures. Run the applicable commands
  in `.repo-context/verification.md`, including its repository-specific options.
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

## Safety

- Inject configuration at construction; keep `os.environ` reads out of business
  logic. Keep secrets out of YAML, Git, and logs.
- Give external I/O explicit timeouts and bounded retries. Keep blocking I/O
  out of async code (use `asyncio.to_thread()` when needed), bound parallel
  `gather()` calls, and never swallow background-task exceptions.
- Parameterize SQL and query inputs; validate user-controlled paths and shell
  arguments. Never use `eval`, `exec`, or unsafe deserialization on untrusted input.
- Log with `structlog`, not `print`; avoid bare `except` clauses.

## Testing

- Exercise behavior through public interfaces. Mock only hard external
  boundaries; prefer parametrization and shared fixtures to repeated bodies.
- For risky behavior changes, write a failing test or characterization test
  first. Reuse the repository's fixtures and markers, and run the applicable
  commands in `.repo-context/verification.md`.

## Package management

- Use uv: `uv sync` for the environment and `uv run` for Python tools/scripts.
- Manage dependencies with `uv add` / `uv remove` (`--dev` for development tools).
  Keep `pyproject.toml` and `uv.lock` consistent; do not use ad hoc pip installs
  as a substitute for declaring project dependencies.
