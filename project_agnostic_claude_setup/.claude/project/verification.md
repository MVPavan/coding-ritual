# Verification Commands

Status: template until `/adopt` runs

Use the adopted commands below when they exist. Do not invent a weaker substitute.

## Adopted Commands

- Quick:
- Full:
- Extended:

Run the repo's own scripts or CI-equivalent commands when they exist. Do not invent a weaker substitute.

## Python Fallback

Use these only if the repo is Python and `/adopt` did not find stronger local commands:

- `ruff check .`
- `ruff format --check .`
- `mypy .`
- `pytest`
