"""Unit tests for §9 payload canonicalization and signature verification.

These run a real `ssh-keygen` against a throwaway key, so they assert the
mechanism as it actually behaves rather than a mock of it. No bd is involved.
"""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from tests.conftest import KEYGEN_TIMEOUT_S, SSH_KEYGEN, TEST_PRINCIPAL, Signer
from workflow_interpreter.bdio.config import SigningConfig
from workflow_interpreter.bdio.errors import (
    BdConfigError,
    GateVerificationError,
    PayloadMismatchError,
    SignatureRefusedError,
    SignerNotAllowedError,
)
from workflow_interpreter.bdio.signing import (
    BoundMutation,
    GateArtifact,
    GatePayload,
    GateVerifier,
    canonical_payload_bytes,
    parse_allowed_signers,
    payload_digest,
)
from workflow_interpreter.bdio.wire import BoundSetting, canonical_json_bytes
from workflow_interpreter.schema.models import Outcome

GRAPH_ID: Final[str] = "feature-delivery"
ROOT_ID: Final[str] = "wf-root"
GATE_KEY: Final[str] = "gk-1"


def _payload(**overrides: object) -> GatePayload:
    """A well-formed immutable-binds approval payload."""
    base: dict[str, object] = {
        "graph_id": GRAPH_ID,
        "root_id": ROOT_ID,
        "gate_key": GATE_KEY,
        "outcome": Outcome.APPROVE,
        "artifact": GateArtifact(commit_oid="c0ffee", tree_oid="7ee"),
        "nonce": "nonce-1",
    }
    return GatePayload.model_validate(base | overrides)


@pytest.fixture
def verifier(signing_config: SigningConfig, tmp_path: Path) -> GateVerifier:
    """A verifier whose allow-list is outside the (simulated) workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return GateVerifier(signing_config, workspace)


def test_canonical_payload_bytes_are_sorted_and_null_free() -> None:
    encoded = canonical_payload_bytes(_payload())
    assert b"bound_mutation" not in encoded
    assert json.loads(encoded)["gate_key"] == GATE_KEY
    keys = list(json.loads(encoded))
    assert keys == sorted(keys)


def test_the_digest_is_over_the_signed_bytes() -> None:
    encoded = canonical_payload_bytes(_payload())
    assert payload_digest(encoded) != payload_digest(encoded + b" ")


def test_a_valid_signature_verifies_and_reports_the_signer(
    verifier: GateVerifier, sign_payload: Signer, tmp_path: Path
) -> None:
    encoded = canonical_payload_bytes(_payload())
    approval = verifier.verify(
        payload_bytes=encoded,
        signature=sign_payload(encoded, None),
        work_dir=tmp_path,
    )
    assert approval.payload == _payload()
    assert approval.principal == TEST_PRINCIPAL
    assert approval.fingerprint in verifier.allowed_fingerprints()
    assert approval.payload_digest == payload_digest(encoded)


def test_a_tampered_payload_is_refused(
    verifier: GateVerifier, sign_payload: Signer, tmp_path: Path
) -> None:
    encoded = canonical_payload_bytes(_payload())
    signature = sign_payload(encoded, None)
    tampered = canonical_payload_bytes(_payload(outcome=Outcome.ABANDON))
    with pytest.raises(SignatureRefusedError):
        verifier.verify(payload_bytes=tampered, signature=signature, work_dir=tmp_path)


def test_a_signer_outside_the_allow_list_is_refused(
    verifier: GateVerifier, sign_payload: Signer, tmp_path: Path
) -> None:
    rogue = tmp_path / "rogue"
    subprocess.run(
        [SSH_KEYGEN, "-t", "ed25519", "-N", "", "-C", "rogue@test", "-f", str(rogue)],
        check=True,
        capture_output=True,
        timeout=KEYGEN_TIMEOUT_S,
    )
    encoded = canonical_payload_bytes(_payload())
    with pytest.raises(SignerNotAllowedError):
        verifier.verify(
            payload_bytes=encoded,
            signature=sign_payload(encoded, rogue),
            work_dir=tmp_path,
        )


def test_a_non_canonical_encoding_is_refused_never_normalized(
    verifier: GateVerifier, sign_payload: Signer, tmp_path: Path
) -> None:
    # Semantically identical, re-encoded with whitespace: a signature over it
    # must not be laundered into a valid approval (§9, mirroring §2 rule 8).
    reencoded = json.dumps(
        json.loads(canonical_payload_bytes(_payload())), indent=2
    ).encode("utf-8")
    with pytest.raises(SignatureRefusedError, match="canonical"):
        verifier.verify(
            payload_bytes=reencoded,
            signature=sign_payload(reencoded, None),
            work_dir=tmp_path,
        )


def test_bytes_that_are_not_a_gate_payload_are_refused(
    verifier: GateVerifier, sign_payload: Signer, tmp_path: Path
) -> None:
    garbage = b'{"not":"a payload"}'
    with pytest.raises(SignatureRefusedError, match="not a valid gate payload"):
        verifier.verify(
            payload_bytes=garbage,
            signature=sign_payload(garbage, None),
            work_dir=tmp_path,
        )


def test_an_allow_list_inside_the_workspace_is_refused(
    signing_config: SigningConfig,
) -> None:
    # §9: a foreman that can write its own allow-list can forge approvals.
    with pytest.raises(BdConfigError, match="inside the bd workspace"):
        GateVerifier(signing_config, signing_config.allowed_signers_path.parent)


def test_a_missing_allow_list_is_refused(tmp_path: Path) -> None:
    with pytest.raises(BdConfigError, match="does not exist"):
        GateVerifier(SigningConfig(allowed_signers_path=tmp_path / "nope"), tmp_path)


# --- allowed_signers grammar (§9 allow-list) -----------------------------


def _allow_list(tmp_path: Path, text: str) -> GateVerifier:
    """A verifier over an allow-list written verbatim."""
    directory = tmp_path / "signers"
    directory.mkdir(exist_ok=True)
    path = directory / "allowed_signers"
    path.write_text(text, encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return GateVerifier(SigningConfig(allowed_signers_path=path), workspace)


def test_the_computed_fingerprint_matches_ssh_keygen(signing_key: Path) -> None:
    # The allow-list fingerprint is now computed from the parsed key blob, so
    # it has to agree with the real tool byte for byte.
    reported = subprocess.run(
        [SSH_KEYGEN, "-lf", str(signing_key.with_suffix(".pub"))],
        check=True,
        capture_output=True,
        text=True,
        timeout=KEYGEN_TIMEOUT_S,
    ).stdout.split()[1]
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8")
    parsed = parse_allowed_signers(f"{TEST_PRINCIPAL} {public}", signing_key)
    assert parsed[0].fingerprint == reported
    assert parsed[0].key_type == "ssh-ed25519"
    assert parsed[0].principals == (TEST_PRINCIPAL,)


def test_an_options_only_allow_list_parses(signing_key: Path, tmp_path: Path) -> None:
    # `ssh-keygen -lf` exits 255 on this file (probed); the old fingerprint
    # extraction therefore refused every approval it should have accepted.
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    verifier = _allow_list(
        tmp_path, f'{TEST_PRINCIPAL} namespaces="wf-gate" {public}\n'
    )
    assert len(verifier.signers) == 1
    assert verifier.signers[0].namespaces == ("wf-gate",)
    assert verifier.allowed_fingerprints() == frozenset(
        {verifier.signers[0].fingerprint}
    )


def test_a_mixed_allow_list_keeps_its_hardened_lines(
    signing_key: Path, tmp_path: Path
) -> None:
    # The hardened line was SILENTLY DROPPED before — the worst failure shape,
    # because the file looks correct and the approval is simply refused.
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    verifier = _allow_list(
        tmp_path,
        "# gate signers\n"
        f"plain@wf-test {public}\n"
        f'hardened@wf-test valid-after="20260101",namespaces="wf-gate,git" {public}\n'
        "\n",
    )
    assert len(verifier.signers) == 2
    assert verifier.signers[0].namespaces == ()
    assert verifier.signers[1].namespaces == ("wf-gate", "git")
    assert verifier.signers[1].principals == ("hardened@wf-test",)


def test_a_namespaces_restriction_excluding_wf_gate_is_honored(
    signing_key: Path, tmp_path: Path
) -> None:
    # A key allowed only for `git` signatures is not an allowed gate signer.
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    with pytest.raises(BdConfigError, match="namespace"):
        _allow_list(tmp_path, f'{TEST_PRINCIPAL} namespaces="git" {public}\n')


def test_a_namespaces_hardened_allow_list_still_verifies_end_to_end(
    signing_key: Path, tmp_path: Path, sign_payload: Signer
) -> None:
    # The whole point of parsing the options field: a correctly hardened
    # allow-list must ACCEPT the approvals it authorizes, all the way through
    # ssh-keygen's own `-Y verify`.
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    verifier = _allow_list(
        tmp_path, f'{TEST_PRINCIPAL} namespaces="wf-gate" {public}\n'
    )
    encoded = canonical_payload_bytes(_payload())
    approval = verifier.verify(
        payload_bytes=encoded, signature=sign_payload(encoded, None), work_dir=tmp_path
    )
    assert approval.principal == TEST_PRINCIPAL


def test_a_namespaces_glob_matches_the_way_openssh_matches_it(
    signing_key: Path, tmp_path: Path
) -> None:
    # OpenSSH matches `namespaces=` values as PATTERNS. `wf-*` permits
    # `wf-gate`; treating the value as a literal refused an allow-list that
    # ssh-keygen itself accepts (probed, round-2 review).
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    verifier = _allow_list(tmp_path, f'{TEST_PRINCIPAL} namespaces="wf-*" {public}\n')
    assert verifier.signers[0].signs_in("wf-gate")
    assert not verifier.signers[0].signs_in("git")
    assert verifier.allowed_fingerprints() == frozenset(
        {verifier.signers[0].fingerprint}
    )


def test_a_namespaces_pattern_list_honours_negation(
    signing_key: Path, tmp_path: Path
) -> None:
    # OpenSSH pattern-LISTS: a match needs a positive pattern AND no negated
    # one. Matching positives only made `namespaces="*,!wf-gate"` permit
    # `wf-gate` — the one direction this parser must never fail in (probed
    # against the local OpenSSH manual, round 3).
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    with pytest.raises(BdConfigError, match="namespace"):
        _allow_list(tmp_path, f'{TEST_PRINCIPAL} namespaces="*,!wf-gate" {public}\n')

    verifier = _allow_list(
        tmp_path, f'{TEST_PRINCIPAL} namespaces="wf-*,!wf-git" {public}\n'
    )
    signer = verifier.signers[0]
    assert signer.signs_in("wf-gate")
    assert not signer.signs_in("wf-git")
    assert not signer.signs_in("git")


def test_a_namespaces_pattern_has_no_character_classes(
    signing_key: Path, tmp_path: Path
) -> None:
    # `*` and `?` are the ONLY metacharacters OpenSSH defines; `fnmatch` also
    # honours `[…]`, which would silently match something else.
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    verifier = _allow_list(
        tmp_path, f'{TEST_PRINCIPAL} namespaces="wf-gate,wf[12]" {public}\n'
    )
    signer = verifier.signers[0]
    assert signer.signs_in("wf[12]")
    assert not signer.signs_in("wf1")


def test_a_truncated_key_blob_is_refused_like_ssh_keygen_refuses_it(
    tmp_path: Path,
) -> None:
    # A blob holding only its type string decodes, yields a type — and is not
    # a key: `ssh-keygen -lf` exits 255 on it while the wrapper fingerprinted
    # it and started up (probed, round 3). The WHOLE wire blob is validated.
    truncated = base64.b64encode(
        len(b"ssh-ed25519").to_bytes(4, "big") + b"ssh-ed25519"
    ).decode("ascii")
    line = f"{TEST_PRINCIPAL} ssh-ed25519 {truncated}\n"
    key_file = tmp_path / "truncated.pub"
    key_file.write_text(line.split(" ", 1)[1], encoding="utf-8")
    reported = subprocess.run(
        [SSH_KEYGEN, "-lf", str(key_file)],
        capture_output=True,
        text=True,
        timeout=KEYGEN_TIMEOUT_S,
        check=False,
    )
    assert reported.returncode != 0

    with pytest.raises(BdConfigError, match="not a valid allowed_signers entry"):
        _allow_list(tmp_path, line)


def test_a_key_blob_with_trailing_bytes_is_refused(
    signing_key: Path, tmp_path: Path
) -> None:
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    _, blob, *_ = public.split()
    padded = base64.b64encode(base64.b64decode(blob) + b"\x00\x01").decode("ascii")
    with pytest.raises(BdConfigError, match="not a valid allowed_signers entry"):
        _allow_list(tmp_path, f"{TEST_PRINCIPAL} ssh-ed25519 {padded}\n")


def test_an_option_keyword_is_matched_case_insensitively(
    signing_key: Path, tmp_path: Path
) -> None:
    # `Namespaces="git"` restricts the key exactly as `namespaces=` does. Reading
    # it case-sensitively dropped the restriction and treated the key as
    # unrestricted — the one direction this parser must never fail in.
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    with pytest.raises(BdConfigError, match="namespace"):
        _allow_list(tmp_path, f'{TEST_PRINCIPAL} Namespaces="git" {public}\n')


def test_a_base64_field_that_is_not_a_key_blob_is_refused(tmp_path: Path) -> None:
    # `ssh-ed25519 AAAA` is valid base64 and was fingerprinted happily, while
    # ssh-keygen reports `invalid key`. The blob's own type string is the
    # authority on what the field holds.
    with pytest.raises(BdConfigError, match="not a valid allowed_signers entry"):
        _allow_list(tmp_path, f"{TEST_PRINCIPAL} ssh-ed25519 AAAA\n")


def test_a_key_blob_contradicting_its_declared_type_is_refused(
    signing_key: Path, tmp_path: Path
) -> None:
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    _, blob, *_ = public.split()
    with pytest.raises(BdConfigError, match="declares type"):
        _allow_list(tmp_path, f"{TEST_PRINCIPAL} ecdsa-sha2-nistp256 {blob}\n")


def test_a_cert_authority_line_is_refused_never_fingerprinted(
    signing_key: Path, tmp_path: Path
) -> None:
    # §9 verifies by fingerprint EQUALITY against named keys. A CA's fingerprint
    # is not the fingerprint of anything that signs, so silently admitting it
    # puts a key on the allow-list that can never match a real approval.
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    with pytest.raises(BdConfigError, match="cert-authority"):
        _allow_list(tmp_path, f"{TEST_PRINCIPAL} cert-authority {public}\n")


def test_multiple_principals_on_one_line_are_all_recorded(
    signing_key: Path, tmp_path: Path
) -> None:
    public = signing_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    verifier = _allow_list(tmp_path, f"alice@wf,bob@wf {public}\n")
    assert verifier.signers[0].principals == ("alice@wf", "bob@wf")


@pytest.mark.parametrize(
    "line",
    [
        "gatekeeper@wf-test",
        "gatekeeper@wf-test ssh-ed25519",
        "gatekeeper ssh-ed25519 !!",
    ],
)
def test_an_unparseable_line_refuses_the_whole_allow_list(
    line: str, tmp_path: Path
) -> None:
    # A key the wrapper cannot read is a key it cannot hold accountable.
    with pytest.raises(BdConfigError, match="not a valid allowed_signers entry"):
        _allow_list(tmp_path, f"{line}\n")


# --- §9 signed-payload semantics -----------------------------------------


def test_a_payload_pinning_another_schema_version_is_refused() -> None:
    # A `wf-gate-payload/2` must not close a v1 gate just because it signs.
    with pytest.raises(PayloadMismatchError, match="schema_version"):
        _payload(schema_version="wf-gate-payload/2")


def test_bound_mutation_is_legal_exactly_when_the_outcome_is_rebudget() -> None:
    mutation = {"key": BoundSetting.MAX_ENTRIES.at("build-review"), "value": 5}
    with pytest.raises(PayloadMismatchError, match="bound_mutation"):
        _payload(outcome=Outcome.APPROVE, bound_mutation=mutation)
    with pytest.raises(PayloadMismatchError, match="bound_mutation"):
        _payload(outcome=Outcome.REBUDGET)
    accepted = _payload(outcome=Outcome.REBUDGET, bound_mutation=mutation)
    assert accepted.bound_mutation is not None
    assert accepted.bound_mutation.value == 5


def test_a_mutation_key_outside_the_bound_vocabulary_is_refused() -> None:
    with pytest.raises(PayloadMismatchError, match="closed bound vocabulary"):
        BoundMutation(key="anything", value=1)


@pytest.mark.parametrize("value", [0, -1])
def test_a_non_positive_bound_value_is_refused(value: int) -> None:
    with pytest.raises(ValidationError):
        BoundMutation(key=BoundSetting.MAX_TOTAL_ACTIVATIONS.at(), value=value)


def test_a_payload_carrying_a_bad_mutation_never_verifies(
    verifier: GateVerifier, sign_payload: Signer, tmp_path: Path
) -> None:
    # The shape rules run on the SIGNED bytes, so a hand-rolled payload that
    # bypasses the model still cannot become a VerifiedApproval.
    hostile = canonical_json_bytes(
        {
            "artifact": {"commit_oid": "c0ffee", "tree_oid": "7ee"},
            "bound_mutation": {"key": "anything", "value": -1},
            "gate_key": GATE_KEY,
            "graph_id": GRAPH_ID,
            "nonce": "nonce-1",
            "outcome": Outcome.APPROVE.value,
            "root_id": ROOT_ID,
            "schema_version": "wf-gate-payload/1",
        }
    )
    # Either refusal class is a GateVerificationError: the gate stays open.
    with pytest.raises(GateVerificationError):
        verifier.verify(
            payload_bytes=hostile,
            signature=sign_payload(hostile, None),
            work_dir=tmp_path,
        )
