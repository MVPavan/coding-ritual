"""E1b/E1c — the §9 key material a live run needs, and the approval helper.

Both scripts are the artefact under test: a §9 approval is exactly "drop
`payload.json` and `payload.json.sig` into the gate inbox", and everything
between the rendered template and those two files was hand-work until now.
The assertions go through the real `GateVerifier` and the real
`close_gate_verified`, because a helper that produces bytes the store refuses
is worse than no helper.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from tests._supervisor import make_repo
from workflow_interpreter.bdio.carriers import GateState
from workflow_interpreter.bdio.config import (
    GATE_SIGNATURE_NAMESPACE,
    SigningConfig,
)
from workflow_interpreter.bdio.signing import GateVerifier
from workflow_interpreter.foreman.config import load_config
from workflow_interpreter.foreman.constants import GATE_NONCE_PLACEHOLDER, GATES_DIR
from workflow_interpreter.foreman.gates import halt_gate, payload_template

pytestmark = pytest.mark.proc

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
GENERATOR = SCRIPTS / "make-foreman-config.sh"
APPROVER = SCRIPTS / "approve-gate.sh"
SCRIPT_TIMEOUT_S = 60.0
SIGNERS = ("signers", "gate_key", "gate_key.pub", "allowed_signers")


def _generate(repo: Path, home: Path, output: Path) -> str:
    """Run the config generator with an isolated `$HOME`; return its stdout."""
    completed = subprocess.run(
        [str(GENERATOR), str(output)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_S,
        env={"HOME": str(home), "PATH": os.environ["PATH"], "USER": "tester"},
    )
    return completed.stdout


def test_the_generator_makes_a_gate_key_and_allow_list_exactly_once(
    tmp_path: Path,
) -> None:
    """E1b: fresh `$HOME` gets parseable key material; a second run changes none."""
    repo = make_repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    output = tmp_path / "foreman.toml"

    first = _generate(repo, home, output)
    config = load_config(output)
    assert config.signing is not None
    verifier = GateVerifier(config.signing, config.bd.workspace)

    assert [signer.principals for signer in verifier.signers] == [("wf-tester",)]
    assert verifier.allowed_fingerprints()
    signers_dir = config.wrapper_home / "signers"
    assert (signers_dir / "gate_key").exists()
    before = {
        name: (signers_dir / name).read_bytes()
        for name in ("gate_key", "gate_key.pub", "allowed_signers")
    }
    # The approver command line must name the real key and the namespace the
    # verifier demands — a wrong `-n` verifies as a signature and refuses as
    # an approval.
    assert f"-n {GATE_SIGNATURE_NAMESPACE}" in first
    assert str(signers_dir / "gate_key") in first

    _generate(repo, home, output)

    assert {name: (signers_dir / name).read_bytes() for name in before} == before


def test_the_approver_signs_a_template_the_store_then_accepts(
    tmp_path: Path, signing_config: SigningConfig, signing_key: Path
) -> None:
    """E1c: template in, `payload.json` + `.sig` in the inbox, gate closed."""
    lab = ForemanLab(tmp_path, signing=signing_config)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))
    inbox = lab.wiring().paths.instance_dir / GATES_DIR / gate.metadata.gate_key
    inbox.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [str(APPROVER), str(inbox), str(signing_key)],
        input=payload_template(root, gate),
        check=True,
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_S,
    )

    payload_bytes = (inbox / "payload.json").read_bytes()
    assert str(inbox / "payload.json") in completed.stdout
    assert str(inbox / "payload.json.sig") in completed.stdout
    nonce = json.loads(payload_bytes)["nonce"]
    assert nonce != GATE_NONCE_PLACEHOLDER
    assert len(nonce) >= 32

    closed = lab.store.close_gate_verified(
        root.root_id,
        gate.gate_id,
        payload_bytes=payload_bytes,
        signature=(inbox / "payload.json.sig").read_bytes(),
    )

    assert closed.metadata.state is GateState.CLOSED
