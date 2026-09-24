#!/usr/bin/env bash
# Explicit context allowlist: never send the repo, local environments or secrets.
set -euo pipefail
cd "$(dirname "$0")/.."
tar -cf - Dockerfile pyproject.toml uv.lock README.md src/dws/__init__.py src/dws/cli.py \
  docker/qmd/package.json docker/qmd/package-lock.json docker/application_build.txt \
  docker/application_entrypoint.sh |
  docker build --platform linux/amd64 --target application \
    --tag dws-application:qualification --progress plain -
