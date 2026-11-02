#!/usr/bin/env python3
"""Snapshot the working tree as tree objects and undo one attempt exactly. Exit 0 ok; 2 refused
with nothing changed; 1 a mismatch, or any failure once the real apply has started, so files
may have changed. 1 and 2 are stops. One writer across the tree: a snapshot covers all of it, so
another's edit between two snapshots reads as part of the attempt.
  snapshot                      print "<tree> <index-tree>"; moves no real index, ref or commit
  patch <from> <to> <x.patch>   write the incremental binary patch between two trees
  undo|replay <x.patch> <tree> <index>   prove the result on a temporary index, refusing with
                                nothing changed; reverse (undo) or apply (replay) it; verify. A
                                failure during the real apply (an ignored file blocking a
                                directory, a write error) may leave part of it applied: exit 1.
  verify <tree> <index>         compare a new snapshot
Outside a snapshot: ignored paths, dirt inside a submodule, a mode change Git ignores
(core.filemode=false). Refused: a sparse tree; any file whose bytes Git would convert going in
or coming out (line endings, filters), since equal trees would not prove it; a patch inside this
tree and not ignored, since it would change the next snapshot; a patch changing a .gitattributes,
since Git reads attributes while applying.
Limit: attributes from outside a snapshot (.git/info/attributes, config) changing during a climb
are not proved first; with a patch that brings a file back, they surface as exit 1."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def stop(code, message):
    print(message, file=sys.stderr)
    sys.exit(code)


def need(*args, env=None):
    done = subprocess.run(
        ["git", *args], env=env, capture_output=True, check=False
    )  # bytes: text mode rewrites CR
    if done.returncode:
        stop(
            2, f"refused: git {args[0]}: {done.stderr.decode(errors='replace').strip()}"
        )
    return done.stdout.decode(errors="surrogateescape")


def snapshot():
    if (
        subprocess.run(
            ["git", "config", "--bool", "core.sparseCheckout"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        == "true"
    ):
        stop(2, "refused: sparse tree")
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        need("read-tree", "HEAD", env=env)
        need("add", "--all", env=env)
        rows = [
            r.split("\t", 1)
            for r in need("ls-files", "-s", "-z", env=env).split("\0")
            if r
        ]
        files = [
            (meta.split()[1], path)
            for meta, path in rows
            if meta[:6] not in ("120000", "160000")
        ]
        for i in range(0, len(files), 500):
            part = files[i : i + 500]
            raw = need(
                "hash-object", "--no-filters", "--", *[p for _, p in part]
            ).split()
            for (blob, path), have in zip(part, raw):
                if blob != have:
                    stop(2, f"refused: Git converts the bytes of {path}")
        # Each file's bytes now equal its blob, so the stream is known in advance. The header's
        # size is the blob's even when the content was converted: never parse by it.
        with tempfile.TemporaryFile() as ask:
            for blob, path in files:
                ask.write(f"{blob} {path}\0".encode(errors="surrogateescape"))
            ask.seek(0)
            with subprocess.Popen(
                ["git", "cat-file", "--batch", "--filters", "-z"],
                env=env,
                stdin=ask,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            ) as out:
                for blob, path in files:
                    raw = Path(path).read_bytes()
                    want = f"{blob} blob {len(raw)}\n".encode() + raw + b"\n"
                    if out.stdout.read(len(want)) != want:
                        stop(2, f"refused: Git converts the bytes of {path}")
                if out.stdout.read(1) or out.wait():
                    stop(
                        2,
                        "refused: Git converts the bytes of a file, or its filter failed",
                    )
        return need("write-tree", env=env).strip(), need("write-tree").strip()


def trees(tree, index):
    return (
        need("rev-parse", f"{tree}^{{tree}}").strip(),
        need("rev-parse", f"{index}^{{tree}}").strip(),
    )


def verify(tree, index):
    want = trees(tree, index)
    if (now := snapshot()) != want:
        stop(1, f"mismatch: have {now}, want {want}")


def preflight(apply, tree, index):
    """Apply to a temporary index and require the wanted result; no file has changed yet."""
    want = trees(tree, index)
    now = snapshot()
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        need("read-tree", now[0], env=env)
        if apply:
            need(apply[0], "--cached", *apply[1:], env=env)
        if (have := (need("write-tree", env=env).strip(), now[1])) != want:
            stop(2, f"refused: the result would be {have}, want {want}")


def main(cmd, *args):
    args = [str(Path(a).resolve()) if a.endswith(".patch") else a for a in args]
    os.chdir(need("rev-parse", "--show-toplevel").strip())
    if cmd == "snapshot":
        print(*snapshot())
    elif cmd == "patch":
        if (
            Path(args[2]).resolve().is_relative_to(Path.cwd().resolve())
            and subprocess.run(
                ["git", "check-ignore", "-q", args[2]], check=False
            ).returncode
        ):
            stop(2, f"refused: {args[2]} is inside this tree and not ignored")
        changed = need("diff", "--name-only", "-z", "--no-renames", args[0], args[1])
        for path in changed.split("\0"):
            if Path(path).name == ".gitattributes":
                stop(
                    2, f"refused: the patch changes {path}; Git reads it while applying"
                )
        flags = "--binary --no-color --no-ext-diff --no-textconv --no-renames --src-prefix=a/ --dst-prefix=b/"
        Path(args[2]).write_bytes(
            need("diff", *flags.split(), args[0], args[1]).encode(
                errors="surrogateescape"
            )
        )
    elif cmd in ("undo", "replay"):
        apply = Path(args[0]).stat().st_size and [
            "apply",
            "--whitespace=nowarn",
            *(["-R"] if cmd == "undo" else []),
            args[0],
        ]
        preflight(apply, *args[1:])
        try:
            if apply:
                need(*apply)
            verify(*args[1:])
        except SystemExit:
            sys.exit(1)  # the apply has started, so exit 2 would be false
    elif cmd == "verify":
        verify(*args)


if __name__ == "__main__":
    main(*sys.argv[1:])
