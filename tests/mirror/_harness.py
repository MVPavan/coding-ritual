"""Harness for the Beads -> GitHub mirror tests: the fake gh, the store and the command.

The seams are the two command-line tools the mirror calls. ``gh`` is the stateful fake
in ``_fake_gh.py``; ``bd`` is the real binary against a real temporary store. Every
run gets a PATH holding only the fake ``gh`` and links to ``git`` and a logging ``bd``
shim, so the real ``gh`` can never be found. The store is initialised once per session
(``bd init`` takes about two seconds) and copied per test (a few milliseconds).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND = REPO_ROOT / ".claude" / "hooks" / "bead-mirror.py"
FAKE_GH = Path(__file__).resolve().parent / "_fake_gh.py"

HOST = "github.com"
REPO = "acme/widgets"
REPO_NODE_ID = "R_kgDOAcmeW1"
ACCOUNT = "mirror-bot"


# Inherited from a hook or the developer's shell, any ``GIT_*`` variable could steer a
# child: ``GIT_DIR`` or ``GIT_WORK_TREE`` point ``git init`` (and every later git call)
# at the caller's repository whatever the working directory, and the global or system
# configuration could redirect initialisation (templates, hooks). All are dropped and
# git reads neither configuration; the identity comes from the environment instead.
# HOME stays: bd keeps its own user configuration there (metrics off), and a
# temporary HOME would change how bd behaves.
GIT_ISOLATION = {
    "DO_NOT_TRACK": "1",  # bd metrics stay off whatever the user setting
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_NAME": "mirror test",
    "GIT_AUTHOR_EMAIL": "mirror-test@example.com",
    "GIT_COMMITTER_NAME": "mirror test",
    "GIT_COMMITTER_EMAIL": "mirror-test@example.com",
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# A shell reads these at startup (or imports functions from them): inherited, they
# could put another directory first on PATH, or replace a command, before the
# configured hook command runs, so the fake gh would no longer be the gh found.
SHELL_STARTUP = ("BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "CDPATH", "PROMPT_COMMAND")


def scrubbed_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("BEADS_", "GH_", "GIT_", "BASH_FUNC_"))
        and k not in SHELL_STARTUP
    }
    env.update(GIT_ISOLATION)
    env.update(extra or {})
    return env


def real_tool(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        pytest.skip(f"{name} is not installed")
    return found


def make_store(path: Path, prefix: str) -> str:
    """A real Beads store in a fresh git repository; returns its project_id."""
    path.mkdir(parents=True)
    env = scrubbed_env()
    subprocess.run(["git", "init", "-q"], cwd=path, env=env, check=True)
    subprocess.run(
        [
            real_tool("bd"),
            "init",
            "--prefix",
            prefix,
            "--non-interactive",
            "--skip-hooks",
            "--skip-agents",
            "--actor",
            "test:mirror",
        ],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            real_tool("bd"),
            "create",
            "A task",
            "-t",
            "task",
            "--actor",
            "test:mirror",
        ],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )
    return str(
        json.loads((path / ".beads" / "metadata.json").read_text())["project_id"]
    )


@dataclass
class Fake:
    """The fake gh's state file, read and written by the test."""

    path: Path

    def load(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(self.path.read_text())
        return data

    def save(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2))

    def set_fault(self, name: str, value: Any) -> None:
        state = self.load()
        state["faults"][name] = value
        self.save(state)

    def set(self, key: str, value: Any) -> None:
        state = self.load()
        state[key] = value
        self.save(state)

    def calls(self) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = self.load()["calls"]
        return calls

    def writes(self) -> list[dict[str, Any]]:
        return [c for c in self.calls() if c.get("write")]

    def creates(self) -> int:
        return sum(1 for c in self.calls() if c.get("write") == "createIssue")

    def routes(self) -> list[str]:
        return [str(c.get("route")) for c in self.calls()]

    def set_issue_state(self, number: int, value: str) -> None:
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        next(i for i in repo["issues"] if i["number"] == number)["state"] = value
        self.save(data)

    def delete_issue(self, number: int) -> None:
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        repo["issues"] = [i for i in repo["issues"] if i["number"] != number]
        self.save(data)

    def repo(self, node_id: str = REPO_NODE_ID) -> dict[str, Any]:
        return next(r for r in self.load()["repos"] if r["node_id"] == node_id)

    def issues(self, node_id: str = REPO_NODE_ID) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = self.repo(node_id)["issues"]
        return issues

    def add_issue(
        self,
        author: str,
        body: str,
        state: str = "OPEN",
        title: str = "seeded",
        updated_at: str | None = None,
    ) -> int:
        """Seed an issue straight into the repository, as another author or tool would.
        Without ``updated_at`` it carries none, so only a full listing sees it."""
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        taken = [i["number"] for i in repo["issues"]] + [
            p["number"] for p in repo["pulls"]
        ]
        number = max(taken, default=0) + 1
        repo["issues"].append(
            {
                "node_id": f"I_kwDOseeded{number}",
                "number": number,
                "author": author,
                "title": title,
                "body": body,
                "labels": [],
                "state": state,
                "comments": [],
                "closing_events": [],
            }
        )
        if updated_at:
            repo["issues"][-1]["updated_at"] = updated_at
        if state == "CLOSED":
            repo["issues"][-1]["closed_at"] = updated_at or now()
        self.save(data)
        return number

    def outside_issue(self, author: str = "alice", title: str = "A report") -> int:
        """An open issue someone outside the mirror opens now."""
        return self.add_issue(
            author, "Seen in the wild.", title=title, updated_at=now()
        )

    def merge_pull(
        self, pull: int, closes: tuple[int, ...] = (), merger: str = "maintainer"
    ) -> str:
        """Merge a pull request now; GitHub closes each issue in ``closes`` with a
        closing event naming it. Returns the merge commit's SHA."""
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        stamp = now()
        sha = f"{pull:07d}".replace("0", "a") + "c0ffee" * 5 + "0f"
        found = next(p for p in repo["pulls"] if p["number"] == pull)
        found.update(
            state="MERGED",
            merged_at=stamp,
            merged_by=merger,
            merge_commit=sha,
            updated_at=stamp,
        )
        for number in closes:
            issue = next(i for i in repo["issues"] if i["number"] == number)
            issue.update(state="CLOSED", closed_at=stamp, updated_at=stamp)
            issue.setdefault("closing_events", []).append(
                {"at": stamp, "closer": {"pull": pull}}
            )
        self.save(data)
        return sha

    def close_issue(self, number: int, commit: str | None = None) -> None:
        """Close an issue now, by hand (or by a pushed commit)."""
        stamp = now()
        closer = {"commit": commit} if commit else None
        events = self.issue(number).get("closing_events") or []
        self.edit_issue(
            number,
            updated_at=stamp,
            state="CLOSED",
            closed_at=stamp,
            closing_events=[*events, {"at": stamp, "closer": closer}],
        )

    def reopen_issue(self, number: int) -> None:
        self.edit_issue(number, state="OPEN", closed_at=None)

    def issue(self, number: int) -> dict[str, Any]:
        return next(i for i in self.issues() if i["number"] == number)

    def edit_issue(
        self, number: int, updated_at: str | None = None, **fields: Any
    ) -> None:
        """Change an issue as a collaborator would; GitHub stamps ``updated_at``."""
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        issue = next(i for i in repo["issues"] if i["number"] == number)
        issue.update(fields)
        issue["updated_at"] = updated_at or time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        self.save(data)

    def add_comment(self, number: int, author: str, body: str) -> None:
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        issue = next(i for i in repo["issues"] if i["number"] == number)
        issue.setdefault("comments", []).append({"author": author, "body": body})
        self.save(data)

    def comments(self, number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = self.issue(number).get("comments", [])
        return comments

    def add_pull(
        self,
        author: str = "contributor",
        body: str | None = None,
        state: str = "OPEN",
    ) -> int:
        """Open a pull request now (``state`` CLOSED: one closed unmerged)."""
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        taken = [i["number"] for i in repo["issues"]] + [
            p["number"] for p in repo["pulls"]
        ]
        number = max(taken, default=0) + 1
        repo["pulls"].append(
            {
                "node_id": f"PR_kwDOseeded{number}",
                "number": number,
                "author": author,
                "body": body,
                "state": state,
                "updated_at": now(),
            }
        )
        self.save(data)
        return number

    def edit_pull(self, number: int, body: str | None) -> None:
        """Save a new pull-request description, as its author would; ``updated_at`` moves."""
        data = self.load()
        repo = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
        pull = next(p for p in repo["pulls"] if p["number"] == number)
        pull.update(body=body, updated_at=now())
        self.save(data)


@dataclass
class Mirror:
    clone: Path
    project_id: str
    fake: Fake
    bin_dir: Path
    tools_dir: Path
    bd_log: Path

    @property
    def mirror_dir(self) -> Path:
        return self.clone / ".git" / "bead-mirror"

    def write_switch(self, **overrides: Any) -> dict[str, Any]:
        switch = {
            "host": HOST,
            "repo": REPO,
            "repo_node_id": REPO_NODE_ID,
            "account": ACCOUNT,
            "scope": ["epic", "feature", "bug"],
            "pr_enrol": True,
            "store_project_id": self.project_id,
        }
        switch.update(overrides)
        self.mirror_dir.mkdir(exist_ok=True)
        (self.mirror_dir / "switch.json").write_text(json.dumps(switch))
        return switch

    def env(
        self, extra: dict[str, str] | None = None, gh_on_path: bool = True
    ) -> dict[str, str]:
        dirs = [str(self.bin_dir)] if gh_on_path else []
        env = scrubbed_env({"PATH": os.pathsep.join(dirs + [str(self.tools_dir)])})
        env["MIRROR_TEST_BD_LOG"] = str(self.bd_log)
        env.update(extra or {})
        return env

    def run(
        self,
        *args: str,
        extra_env: dict[str, str] | None = None,
        gh_on_path: bool = True,
        background: bool = False,
    ) -> Any:
        argv = [sys.executable, str(COMMAND), *args]
        env = self.env(extra_env, gh_on_path)
        if background:
            return subprocess.Popen(
                argv,
                cwd=self.clone,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
            )
        return subprocess.run(
            argv,
            cwd=self.clone,
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )

    def store_snapshot(self) -> str:
        """Every bead in the store, as ``bd export`` prints it."""
        proc = subprocess.run(
            [real_tool("bd"), "export"],
            cwd=self.clone,
            env=scrubbed_env(),
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout

    def bd(self, *args: str) -> str:
        """Run the real bd in the clone (as the test, not the mirror)."""
        proc = subprocess.run(
            [real_tool("bd"), *args, "--actor", "test:mirror"],
            cwd=self.clone,
            env=scrubbed_env(),
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()

    def create_bead(self, title: str, kind: str = "feature", *extra: str) -> str:
        return self.bd("create", title, "-t", kind, "--silent", *extra)

    def beads(self) -> dict[str, dict[str, Any]]:
        rows = [json.loads(line) for line in self.store_snapshot().splitlines() if line]
        return {r["id"]: r for r in rows}

    def state(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads((self.mirror_dir / "state.json").read_text())
        return data

    def binding(self) -> dict[str, str]:
        """The binding a state file for this clone's switch carries."""
        return {
            "store_project_id": self.project_id,
            "repo_node_id": REPO_NODE_ID,
            "account": ACCOUNT,
        }

    def save_state(self, data: dict[str, Any]) -> None:
        (self.mirror_dir / "state.json").write_text(json.dumps(data))

    def import_row(self, bead: str, **fields: Any) -> None:
        """Set fields Beads' commands cannot (a recorded close time) through ``bd import``."""
        row = dict(self.beads()[bead], **fields)
        path = self.clone.parent / f"import-{bead}.jsonl"
        path.write_text(json.dumps(row) + "\n")
        self.bd("import", str(path), "--allow-stale")

    def bd_calls(self) -> list[str]:
        return self.bd_log.read_text().splitlines() if self.bd_log.exists() else []

    def mirror_files(self) -> list[str]:
        if not self.mirror_dir.exists():
            return []
        return sorted(p.name for p in self.mirror_dir.iterdir())


def initial_fake_state() -> dict[str, Any]:
    owner, name = REPO.split("/")
    return {
        "host": HOST,
        "login": ACCOUNT,
        "repos": [
            {
                "node_id": REPO_NODE_ID,
                "owner": owner,
                "name": name,
                "labels": [],
                "issues": [],
                "pulls": [],
            }
        ],
        "faults": {},
        "calls": [],
        "unrecognised": [],
    }


def banner(project_id: str, bead: str, retired: bool = False) -> str:
    mark = " retired" if retired else ""
    return f"<!-- bead-mirror v1 store={project_id} bead={bead}{mark} -->"


def assert_only_links_changed(before: str, after: str, linked: set[str]) -> None:
    """Spec criterion Only the link: the store differs only in ``external_ref`` (and the
    ``updated_at`` that write stamps) on the beads in ``linked``."""

    def rows(text: str) -> dict[str, dict[str, Any]]:
        parsed = [json.loads(line) for line in text.splitlines() if line]
        return {r["id"]: r for r in parsed}

    old, new = rows(before), rows(after)
    assert old.keys() == new.keys()
    for bead_id, row in new.items():
        if bead_id in linked:
            assert row.get("external_ref"), f"{bead_id} has no link"
            row = {
                k: v for k, v in row.items() if k not in ("external_ref", "updated_at")
            }
            was = {
                k: v
                for k, v in old[bead_id].items()
                if k not in ("external_ref", "updated_at")
            }
            assert row == was, f"{bead_id} changed beyond its link"
        else:
            assert row == old[bead_id], f"{bead_id} changed"
