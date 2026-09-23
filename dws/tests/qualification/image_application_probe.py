"""Run inside the application image; synthetic lexical/runtime qualification only."""

from __future__ import annotations

import importlib.metadata
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=45)
    print(json.dumps({"argv": args, "stdout": result.stdout, "stderr": result.stderr}))
    return result.stdout


def main() -> None:
    assert os.umask(0o077) == 0o077
    assert os.getuid() == os.getgid() == 1000
    status = Path("/proc/self/status").read_text()
    assert "CapEff:\t0000000000000000" in status
    assert "NoNewPrivs:\t1" in status
    assert sorted(p.name for p in Path("/sys/class/net").iterdir()) == ["lo"]
    assert not list(Path("/state/cache").rglob("*"))
    assert not Path("/opt/qmd/node_modules/@modelcontextprotocol").exists()
    packages = {
        p.metadata["Name"].lower(): p.version for p in importlib.metadata.distributions()
    }
    assert packages == {"dws": "0.0.1"}, packages
    import dws

    assert dws.__file__ and dws.__file__.startswith("/opt/dws/lib/")
    assert "scaffold" in run("dws", "--help")
    assert run("dws", "--version").strip() == "dws 0.0.1"
    node = run(
        "node",
        "-e",
        """
const D=require('/opt/qmd/node_modules/better-sqlite3');const d=new D(':memory:');
require('/opt/qmd/node_modules/sqlite-vec').load(d);
console.log(JSON.stringify({node:process.version,abi:process.versions.modules,
qmd:require('/opt/qmd/node_modules/@tobilu/qmd/package.json').version,
better_sqlite3:require('/opt/qmd/node_modules/better-sqlite3/package.json').version,
sqlite:d.prepare('select sqlite_version() v').get().v,
vec:d.prepare('select vec_version() v').get().v}));d.close();
""",
    )
    identity = json.loads(node)
    assert identity == {
        "node": "v22.22.0",
        "abi": "127",
        "qmd": "2.8.3",
        "better_sqlite3": "13.0.3",
        "sqlite": "3.53.4",
        "vec": "v0.1.9",
    }
    assert sys.version_info[:3] == (3, 13, 12)
    print(
        json.dumps(
            {
                "python": sys.version,
                "python_sqlite": sqlite3.sqlite_version,
                "packages": packages,
                "module": dws.__file__,
                "native": identity,
            }
        )
    )
    corpus = Path("/state/archive")
    assert corpus.stat().st_mode & 0o777 == 0o700
    if sys.argv[1] == "seed":
        (corpus / "retained.md").write_text("# Fixture\n\ncobaltlexicalneedle retained text.\n")
        run("qmd", "collection", "add", str(corpus), "--name", "fixture")
        run("qmd", "update")
    else:
        assert (corpus / "retained.md").stat().st_mode & 0o777 == 0o600
    run("qmd", "status")
    results = json.loads(run("qmd", "search", "cobaltlexicalneedle", "--json", "-c", "fixture"))
    assert any(row["file"] == "qmd://fixture/retained.md" for row in results)
    assert "retained text" in run("qmd", "get", "qmd://fixture/retained.md")
    if sys.argv[1] == "persist":
        (corpus / "retained.md").write_text("# Changed\n\namberlexicalneedle replacement.\n")
        run("qmd", "update")
        assert (
            json.loads(run("qmd", "search", "cobaltlexicalneedle", "--json", "-c", "fixture"))
            == []
        )
        assert json.loads(run("qmd", "search", "amberlexicalneedle", "--json", "-c", "fixture"))
    assert not list(Path("/state/cache").rglob("*"))
    assert not list(Path("/state/home").rglob("*"))
    print("APPLICATION_PROBE_PASSED", sys.argv[1])


if __name__ == "__main__":
    main()
