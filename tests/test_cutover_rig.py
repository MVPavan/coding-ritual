"""The S3 rig: one stage lands end to end through the PRODUCTION wiring.

`tests/test_cutover.py` drives the same acceptance through doubles — it
replaces `_composition`, `PhaseAdapter.from_config` and `Foreman.run`, and its
bd side is `FakeBd`. Those tests are fast and they are kept, but between them
and production sit the three things they replace: the composition root that
decides which store a root is CREATED through, the adapter that talks to a real
`bd` binary, and the real tick loop. A cutover asserted only through doubles is
a cutover asserted against the test's own wiring (run-ledger §6, S3).

So this file builds what production builds: a foreman TOML, a real bd
workspace, a real ledger in a real repository, and `foreman phase-bridge`
through `__main__.main`. The only stand-in is the vendor binary, which is a
shell stub — the same device the `proc` family uses to drive a real
`Supervisor.run` without spending tokens.

`bd`-marked and slow by design: it forks detached wrappers and shells out to
`bd`, which is exactly the round trip the ledger backend exists to remove, so
the wall of each backend is measured here rather than claimed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Final

import pytest

from tests._supervisor import make_repo
from tests.conftest import Signer
from workflow_interpreter.bdio import GatePayload, Outcome, canonical_payload_bytes
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.models import PhaseBridgeState
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.foreman.gates import payload_template
from workflow_interpreter.ledger.tasks import export_oid, task_backend
from workflow_interpreter.supervisor.paths import fsync_dir

BD_BINARY: Final[str] = "bd"
BD_TIMEOUT_S: Final[float] = 60.0
RIG_WALL_BUDGET_S: Final[float] = 600.0
"""A ceiling, not a target: what the rig may take before it is a hang."""
STUB_MARKER: Final[str] = '{"outcome":"%s"}'
FEATURE_FILE: Final[str] = "src/feature.py"
FEATURE_BODY: Final[str] = "value = 2\n"
SHIP_GATE: Final[str] = "ship"
BEAD_CLOSED: Final[str] = "closed"
PROOF_SCRIPT: Final[str] = (
    "from pathlib import Path; assert Path('src/feature.py').is_file()"
)
"""The repository gate the landing runs in its own detached verify tree."""

_STUB: Final[str] = """#!/bin/sh
# A stand-in for the vendor CLI: emits claude's JSONL shape, writes the two
# channels the wrapper grades on, and — when it is the writer — commits the
# feature it claims to have implemented.
set -e
printf '%s\\n' '{"type":"system","subtype":"init","session_id":"SID","tools":[]}'
printf '%s\\n' '{"type":"result","subtype":"success","session_id":"SID",\
"is_error":false,"result":"ok","total_cost_usd":0.1,\
"usage":{"input_tokens":11,"output_tokens":22}}'
# Which role this is, asked of the §2 mount bound rather than of the
# environment: the writer's node grants `src/**` and the reviewer's grants
# nothing in the checkout, and that IS the difference between the two nodes.
if touch src/.wf-stub-probe 2>/dev/null; then
  rm -f src/.wf-stub-probe
  printf '%s' "$WF_BODY" > "$WF_FEATURE"
  git add "$WF_FEATURE"
  git -c user.email=stub@wf -c user.name=stub commit --quiet -m "stub feature"
  printf '%s' "$WF_MARKER_DONE" > "$WF_OUTCOME_FILE"
  printf '{"paths":["%s"]}' "$WF_FEATURE" > "$WF_EFFECTS_FILE"
else
  printf '%s' "$WF_MARKER_ACCEPT" > "$WF_OUTCOME_FILE"
  printf '%s' '{"paths":[]}' > "$WF_EFFECTS_FILE"
fi
printf 'from the stub\\n' > "$WF_ARTIFACT_DIR/note.txt"
exit 0
"""


def _bd(workspace: Path, *args: str) -> str:
    """One real `bd` command in the throwaway workspace."""
    return (
        subprocess.check_output([BD_BINARY, *args], cwd=workspace, timeout=BD_TIMEOUT_S)
        .decode()
        .strip()
    )


def _status_of(shown: object) -> str:
    """The status of the one bead `bd show --json` answered with."""
    rows = shown if isinstance(shown, list) else [shown]
    assert len(rows) == 1, rows
    row = rows[0]
    assert isinstance(row, dict)
    return str(row["status"])


def _stub_binary(directory: Path) -> Path:
    """The vendor stand-in every role in this rig is bound to."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "stub-claude"
    path.write_text(_STUB.replace("SID", uuid.uuid4().hex), encoding="utf-8")
    path.chmod(0o755)
    return path


def _config_file(
    *,
    repo: Path,
    wrapper_home: Path,
    bd_workspace: Path,
    allowed_signers: Path,
    graph: Path,
    stub: Path,
    store: BackendKind,
) -> Path:
    """The production TOML `load_config` reads, with a stub for the vendor."""
    wrapper_root = (
        wrapper_home / hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:16]
    )
    path = repo.parent / "foreman.toml"
    path.write_text(
        f'repo_root = "{repo}"\n'
        f'wrapper_home = "{wrapper_home}"\n'
        'host = "rig"\n'
        'actor = "rig"\n'
        f'store = "{store.value}"\n'
        f'bridge_graph = "{graph}"\n'
        "[bd]\n"
        f'workspace = "{bd_workspace}"\n'
        'actor = "rig"\n'
        "[signing]\n"
        f'allowed_signers_path = "{allowed_signers}"\n'
        "[profiles]\n"
        f'binary_overrides = {{ claude = "{stub}" }}\n'
        'passthrough_env = ["PATH", "HOME", "WF_BODY", '
        '"WF_FEATURE", "WF_MARKER_DONE", "WF_MARKER_ACCEPT"]\n'
        "[roles.implementer]\n"
        'profile = "claude"\n'
        'model = "stub-model"\n'
        'effort = "low"\n'
        "[roles.critic]\n"
        'profile = "claude"\n'
        'model = "stub-model"\n'
        'effort = "low"\n'
        "[supervisor]\n"
        f'repo_root = "{repo}"\n'
        f'wrapper_root = "{wrapper_root}"\n'
        'host = "rig"\n'
        'sandbox = "bwrap"\n'
        "poll_interval_s = 0.5\n"
        "term_grace_s = 2.0\n"
        "kill_grace_s = 2.0\n"
        "[[bridge_checks]]\n"
        'name = "source-proof"\n'
        f"argv = {json.dumps([sys.executable, '-c', PROOF_SCRIPT])}\n",
        encoding="utf-8",
    )
    return path


def _composition_for(config: Path, task_id: str) -> Composition:
    """The production composition root, for the assertions and the approval."""
    return main_module._composition(
        argparse.Namespace(config=config, task=task_id, stage_id=None)
    )


def _approve_ship(config: Path, stage_id: str, signer: Signer) -> None:
    """Drop the signed approval the next tick intakes, as a human does."""
    composition = _composition_for(config, stage_id)
    try:
        record = PhaseAdapter.from_config(composition.config.bd).record(stage_id)
        root_id = record.root_id or ""
        reads = composition.reads_for_root(root_id)
        root = reads.load_root(root_id)
        gate = next(
            gate
            for gate in reads.list_gates(root_id)
            if gate.metadata.gate_node == SHIP_GATE
        )
        rendered = GatePayload.model_validate_json(payload_template(root, gate))
        payload = rendered.model_copy(
            update={"outcome": Outcome.APPROVE, "nonce": uuid.uuid4().hex}
        )
        payload_bytes = canonical_payload_bytes(payload)
        directory = (
            composition.for_root(root_id).paths.instance_dir
            / "gates"
            / gate.metadata.gate_key
        )
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "payload.json").write_bytes(payload_bytes)
        (directory / "payload.json.sig").write_bytes(signer(payload_bytes, None))
        fsync_dir(directory)
    finally:
        if composition.ledger is not None:
            composition.ledger.close()


@pytest.mark.bd
@pytest.mark.acceptance
@pytest.mark.parametrize("store", (BackendKind.BD, BackendKind.LEDGER))
def test_a_stage_lands_end_to_end_on_a_real_rig(
    tmp_path: Path,
    bd_workspace: Path,
    signing_key: Path,
    sign_payload: Signer,
    monkeypatch: pytest.MonkeyPatch,
    store: BackendKind,
) -> None:
    """prepare → admit → activations → gate → landing → close, for real.

    The assertions are the ones only a production rig can make: the bead a real
    `bd` closed, the root created on the backend the bridge record pins, and —
    on the ledger side — `tasks.export_oid`, which is what §3.6 makes closure
    conditional on.
    """
    repo = make_repo(tmp_path)
    graph = Path(__file__).resolve().parents[1] / (
        "workflow_interpreter/fixtures/legacy/feature-delivery.toml"
    )
    stub = _stub_binary(tmp_path / "bin")
    config = _config_file(
        repo=repo,
        wrapper_home=tmp_path / "wrapper",
        bd_workspace=bd_workspace,
        allowed_signers=signing_key.parent / "allowed_signers",
        graph=graph,
        stub=stub,
        store=store,
    )
    for name, value in (
        ("WF_BODY", FEATURE_BODY),
        ("WF_FEATURE", FEATURE_FILE),
        ("WF_MARKER_DONE", STUB_MARKER % "done"),
        ("WF_MARKER_ACCEPT", STUB_MARKER % "accept"),
    ):
        monkeypatch.setenv(name, value)
    epic = _bd(
        bd_workspace,
        "create",
        "--title",
        f"rig {store.value}",
        "--type",
        "epic",
        "--silent",
    )
    stage = _bd(
        bd_workspace,
        "create",
        "--title",
        f"rig stage {store.value}",
        "--parent",
        epic,
        "--description",
        "Implement the rig feature",
        "--silent",
    )

    started = time.monotonic()
    argv = ["--config", str(config), "phase-bridge", epic, stage]
    assert main_module.main(argv) == 0
    _approve_ship(config, stage, sign_payload)
    assert main_module.main(argv) == 0
    wall_s = time.monotonic() - started

    composition = _composition_for(config, stage)
    try:
        record = PhaseAdapter.from_config(composition.config.bd).record(stage)
        assert record.root_backend is store
        assert record.state is PhaseBridgeState.CLOSED
        shown = json.loads(_bd(bd_workspace, "show", stage, "--json"))
        assert _status_of(shown) == BEAD_CLOSED
        assert (record.root_id or "").startswith(f"{stage}-a") is (
            store is BackendKind.LEDGER
        )
        assert task_backend(composition.ledger, stage) is store
        # §3.6 on BOTH backends: the bead closed only after the task's record
        # was exported and pinned, and the ledger holds that oid even for a
        # bd-backed root, whose landing journal it carries (D17).
        assert record.export_oid is not None
        assert export_oid(composition.ledger, stage) == record.export_oid
    finally:
        if composition.ledger is not None:
            composition.ledger.close()
    assert wall_s < RIG_WALL_BUDGET_S
