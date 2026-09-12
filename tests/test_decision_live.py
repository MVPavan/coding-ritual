"""Real ordinary Codex decision → useful work → preserved human gate.

Run explicitly with --run-live. No fixture signatures or production gates are closed.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.live


def test_real_decision_resumes_work_and_preserves_human_gate(tmp_path: Path) -> None:
    engine = Path(__file__).resolve().parents[1]
    repo = tmp_path / "repo"
    repo.mkdir()
    wrapper = tmp_path / "wrapper"
    for binary in ("git", "bd", "codex", "bwrap"):
        assert shutil.which(binary), f"live proof requires {binary}"

    def execute(
        argv: list[str], name: str, *, cwd: Path = repo, timeout: float = 180
    ) -> str:
        env = {**os.environ, "PYTHONPATH": str(engine)}
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        (tmp_path / f"{name}.stdout").write_text(result.stdout)
        (tmp_path / f"{name}.stderr").write_text(result.stderr)
        assert result.returncode == 0, (
            f"{name} failed ({result.returncode}); evidence {tmp_path}: {result.stderr[-3000:]}"
        )
        return result.stdout

    execute(["git", "init", "-q", "-b", "proof-main"], "git-init")
    execute(["git", "config", "user.name", "Decision proof fixture"], "git-name")
    execute(["git", "config", "user.email", "fixture@example.invalid"], "git-email")
    (repo / "scripts").mkdir()
    (repo / "scripts/verify-feature.sh").write_text(
        "#!/bin/sh\nset -eu\ntest -f scripts/verify-feature.sh\n"
    )
    (repo / "scripts/verify-feature.sh").chmod(0o755)
    # Verifier checks source integrity normally; proof assertion checks the actual output tree.
    shutil.copyfile(
        engine / "workflow_interpreter/fixtures/valid/bounded-decision.toml",
        repo / "proof.toml",
    )
    (repo / ".gitignore").write_text(".beads/\n")
    execute(
        ["git", "add", "scripts/verify-feature.sh", "proof.toml", ".gitignore"],
        "git-stage",
    )
    execute(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "Initialize disposable decision proof",
        ],
        "git-commit",
    )
    execute(
        [
            "bd",
            "init",
            "--prefix",
            "p2live",
            "--non-interactive",
            "--skip-hooks",
            "--skip-agents",
            "--actor",
            "codex:p2-live",
        ],
        "bd-init",
    )
    rootdir = wrapper / hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:16]
    config = tmp_path / "foreman.toml"
    config.write_text(f"""repo_root = {json.dumps(str(repo))}
wrapper_home = {json.dumps(str(wrapper))}
host = {json.dumps(socket.gethostname())}
actor = "codex:p2-live"
[bd]
workspace = {json.dumps(str(repo))}
actor = "codex:p2-live"
[supervisor]
repo_root = {json.dumps(str(repo))}
wrapper_root = {json.dumps(str(rootdir))}
host = {json.dumps(socket.gethostname())}
[roles.implementer]
profile = "codex"
model = "gpt-6-astra"
effort = "low"
[roles.critic]
profile = "codex"
model = "gpt-6-astra"
effort = "low"
""")
    command = [
        sys.executable,
        "-m",
        "workflow_interpreter.foreman",
        "--config",
        str(config),
    ]
    root = execute(
        [
            *command,
            "create",
            str(repo / "proof.toml"),
            "--instance-key",
            "p2-live",
            "--allow-unsigned-gates",
        ],
        "create",
    ).strip()
    (tmp_path / "proof-manifest.json").write_text(
        json.dumps(
            {
                "root": root,
                "repo": str(repo),
                "config": str(config),
                "wrapper": str(rootdir),
            },
            indent=2,
        )
    )
    result = json.loads(
        execute(
            [*command, "run", root, "--poll", "0.1", "--max-wall", "600"],
            "run",
            timeout=660,
        )
    )
    status = json.loads(execute([*command, "status", root], "status"))
    assert result["open_gates"], result
    request = status["coordination"]["requests"][0]
    assert request["state"] == "applied", status
    assert request["response"]["action"] == "continue_declared", request
    assert any(g["node"] == "ship" for g in status["open_gates"]), status
    # Query authoritative carriers independently of the CLI renderer.
    from workflow_interpreter.foreman.__main__ import _composition

    composition = _composition(config)
    records = composition.store.reads.list_activations(root)
    work = next(a for a in records if a.metadata.node == "work")
    evidence = work.metadata.evidence
    assert evidence is not None and evidence.outputs_tree_oid is not None
    assert json.loads(
        composition.git.blob_text(f"{evidence.outputs_tree_oid}:result.json", cwd=repo)
    ) == {"sum": 55}
    gate = next(
        g
        for g in composition.store.reads.list_gates(root)
        if g.metadata.gate_node == "ship"
    )
    assert (
        gate.metadata.state.value == "open"
        and gate.metadata.verified_fingerprint is None
    )
    decider = composition.store.reads.load_activation(request["attempt_id"])
    assert decider.metadata.evidence is not None
    log = rootdir / request["decision_root_id"] / request["attempt_id"] / "run.jsonl"
    # The CLI emits this startup banner before its JSON event stream.
    events = [
        json.loads(line)
        for line in log.read_text().splitlines()
        if line.strip() and line != "Reading additional input from stdin..."
    ]
    thread = next(
        event["thread_id"] for event in events if event.get("type") == "thread.started"
    )
    sessions = (
        Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions"
    )
    rollouts = list(sessions.rglob(f"*{thread}*.jsonl"))
    assert len(rollouts) == 1, (
        f"backend evidence for actual thread {thread} unavailable"
    )
    contexts = []
    for line in rollouts[0].read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "turn_context":
            payload = event["payload"]
            contexts.append(
                {"model": payload.get("model"), "effort": payload.get("effort")}
            )
    assert any(c["model"] == "gpt-6-astra" for c in contexts), contexts
    (tmp_path / "runtime-evidence.json").write_text(
        json.dumps(
            {
                "decision_root": request["decision_root_id"],
                "attempt": request["attempt_id"],
                "thread_id": thread,
                "observed_turn_contexts": contexts,
                "rollout": str(rollouts[0]),
                "response_digest": request["response_digest"],
                "work_activation": work.activation_id,
                "work_output_tree": evidence.outputs_tree_oid,
                "human_gate": gate.gate_id,
                "human_gate_state": gate.metadata.state.value,
                "reserved_capacity": status["coordination"][
                    "reserved_activation_capacity"
                ],
            },
            indent=2,
        )
    )
