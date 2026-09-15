#!/usr/bin/python3
"""Pinned acceptance checks for the bounded DWS package pilot."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def run(argv, cwd, env):
    print('+', ' '.join(argv), flush=True)
    subprocess.run(argv, cwd=cwd, env=env, check=True, timeout=240)


def main():
    root = Path.cwd()
    baseline = json.loads((root / 'docs/verification/dws/pilot-baseline.json').read_text())
    for name, expected in baseline['root_files'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Root source changed: ' + name)
    dws = root / 'dws'
    for required in ['pyproject.toml', 'uv.lock']:
        if not (dws / required).is_file():
            raise SystemExit('Missing independent DWS package file: ' + required)
    with tempfile.TemporaryDirectory(prefix='dws-pilot-check-') as scratch:
        env = dict(os.environ, UV_CACHE_DIR=scratch + '/uv-cache')
        run(['uv', 'sync', '--locked'], dws, env)
        run(['uv', 'run', '--locked', 'dws', '--help'], dws, env)
        run(['uv', 'run', '--locked', 'pytest', '-q'], dws, env)
        run(['uv', 'run', '--locked', 'ruff', 'check', '.'], dws, env)
        run(['uv', 'run', '--locked', 'ruff', 'format', '--check', '.'], dws, env)
        run(['uv', 'run', '--locked', 'mypy', '--strict', 'src/dws'], dws, env)
        run(['uv', 'build', '--wheel', '--out-dir', scratch + '/dist'], dws, env)
        result = subprocess.run(['uv', 'run', '--locked', 'pytest', '--collect-only', '-q'],
                                cwd=root, env=env, capture_output=True, text=True,
                                check=True, timeout=240)
        ids = [line for line in result.stdout.splitlines() if '::' in line and not line.startswith(' ')]
        if hashlib.sha256('\n'.join(ids).encode()).hexdigest() != baseline['collection_sha256']:
            raise SystemExit('Root test collection changed')
    print('DWS acceptance passed; root collection unchanged:', len(ids))


if __name__ == '__main__':
    main()
