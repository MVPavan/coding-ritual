# Python Coding Style

This template is Python-first. If the adopted project uses another language, local project conventions override this file.

- Follow the project's existing Python version and style conventions first.
- Type annotate public functions and important internal boundaries.
- Prefer simple functions, explicit names, and predictable control flow.
- Prefer dataclasses, enums, `TypedDict`, or the project's chosen data-model library when they make data contracts clearer.
- Use `ruff` for linting and formatting and `mypy` for type checking when the repo supports them.
- Avoid bare `except`, mutable defaults, hidden mutation, and global state.
- Keep side effects at the boundary; keep business logic easy to test.
- Use logging instead of `print()` in library or service code.
