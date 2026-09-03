"""Drill 13 against the REAL `scripts/verify-feature.sh`.

The earlier drill-13 coverage rewrites a synthetic one-line check; this one
pins the bytes the phase actually ships and then edits them the way a runner
could — by committing a changed `scripts/verify-feature.sh` after `create`
took the digest. The refusal has to be about THAT: a present, runnable,
different-digest verifier, not a missing one (a missing script also fails
provenance, for a reason this drill is not about).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from tests._supervisor import VERIFY_SCRIPT, ChildScript
from tests.checks._project import VERIFY_FEATURE
from tests.conftest import Signer
from workflow_interpreter.bdio import Outcome, SigningConfig
from workflow_interpreter.supervisor.models import AuditFlag, CompletionEvidence
from workflow_interpreter.supervisor.paths import read_record

pytestmark = pytest.mark.proc

REFUSED_EXIT_CODE = 126
EDIT = "# edited after the pin\n"


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def test_drill_13_refuses_the_real_verifier_when_it_is_edited_after_create(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """An edited pinned verifier is REFUSED, and the claim becomes `fail_code`."""
    pinned_body = VERIFY_FEATURE.read_text(encoding="utf-8")
    edited_body = pinned_body + EDIT
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.pin_checks({VERIFY_SCRIPT: pinned_body})
    lab.instantiate()
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects=f'{{"paths":["{VERIFY_SCRIPT}"]}}',
            write_path=VERIFY_SCRIPT,
            write_body=edited_body,
            commit=True,
        )
    )
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id

    completion = read_record(
        lab.wiring().paths.completion(activation_id), CompletionEvidence
    )

    assert completion is not None
    assert completion.claimed_outcome is Outcome.DONE
    assert completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.VERIFIER_PROVENANCE in completion.audit_flags
    result = next(
        result for result in completion.verify_results if result.cmd == VERIFY_SCRIPT
    )
    assert result.provenance_ok is False
    # The edited-after-pin case specifically: the file IS there and IS a
    # verifier, its digest is simply not the one `create` pinned.
    assert result.script_digest == _digest(edited_body)
    assert result.pinned_digest == _digest(pinned_body)
    assert result.exit_code == REFUSED_EXIT_CODE
