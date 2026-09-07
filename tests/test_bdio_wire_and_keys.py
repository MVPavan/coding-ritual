"""Unit tests for the §3 carriers and the deterministic natural keys.

No bd process is involved: these assert the wire contract itself — what gets
serialized, what comes back, and that two ticks deriving the same key really
do get the same string.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from workflow_interpreter.bdio import keys
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.wire import (
    ActivationMetadata,
    ArtifactIdentity,
    BeadRecord,
    BindsMode,
    BoundSetting,
    EventPayload,
    Evidence,
    GateMetadata,
    GateOpenRequest,
    GateReason,
    InputBinding,
    Lifecycle,
    MintReason,
    MintRequest,
    ProcessHandle,
    Usage,
    VerifyOutcome,
    WfKind,
    canonical_json_bytes,
    metadata_dict,
    parse_bound_key,
)
from workflow_interpreter.schema.models import Outcome

ROOT_ID = "wf-root"
NODE = "implement"


def _activation(**overrides: object) -> ActivationMetadata:
    """A minimal, valid activation carrier."""
    base = {
        "wf_root_id": ROOT_ID,
        "node": NODE,
        "region": "build-review",
        "round_no": 1,
        "seq": 3,
        "idempotency_key": "k",
        "mint_reason": MintReason.ENTRY,
        "runner_profile": "profile:implementer",
        "model": "default",
        "session_id": "sess-1",
        "intended_base_commit": "abc123",
    }
    return ActivationMetadata.model_validate(base | overrides)


def test_activation_round_trips_through_json() -> None:
    metadata = _activation(
        inputs=(
            InputBinding(
                name="task_brief",
                producer_activation_id="wf-1",
                artifact_ref="refs/wf/x",
                digest="sha256:abc",
            ),
        ),
        handle=ProcessHandle(
            pid=1,
            pgid=1,
            host="h",
            host_boot_id="b",
            proc_start_time="t",
            started_at="s",
            log_path="/tmp/log",
            session_id="sess-1",
        ),
        evidence=Evidence(
            verify=(VerifyOutcome(cmd="scripts/v.sh", exit_code=0, script_digest="d"),),
            artifact=ArtifactIdentity(commit_oid="c", tree_oid="t"),
        ),
        lifecycle=Lifecycle.DISPATCHED,
    )
    dumped = metadata_dict(metadata)
    # The bd carrier is JSON: what survives a JSON round-trip is what bd stores.
    reparsed = ActivationMetadata.model_validate(json.loads(json.dumps(dumped)))
    assert reparsed == metadata


def test_metadata_dict_elides_nulls_so_a_merge_never_clears() -> None:
    dumped = metadata_dict(_activation())
    assert "outcome" not in dumped
    assert "handle" not in dumped
    assert dumped["wf_kind"] == WfKind.ACTIVATION.value


def test_usage_from_an_old_wire_record_defaults_new_cache_fields() -> None:
    """A stored `input_tokens=92` record must parse with cache fields as `None`."""
    usage = Usage.model_validate({"known": True, "input_tokens": 92})

    assert usage.cache_read_input_tokens is None
    assert usage.cache_creation_input_tokens is None
    assert usage.total_input_tokens == 92


def test_event_payload_uses_the_reserved_from_and_to_keys() -> None:
    payload = EventPayload(
        from_node="implement",
        outcome=Outcome.DONE,
        to_node="review",
        activation_id="wf-1",
        seq=4,
        actor="foreman",
    )
    dumped = metadata_dict(payload)
    assert dumped["from"] == "implement"
    assert dumped["to"] == "review"
    assert EventPayload.model_validate(dumped) == payload


def test_carriers_reject_unknown_metadata_keys() -> None:
    # An unexpected key on a workflow bead is tamper evidence, not noise (§0).
    with pytest.raises(ValueError, match="extra_forbidden|Extra inputs"):
        ActivationMetadata.model_validate(metadata_dict(_activation()) | {"x": 1})


def test_superseded_activation_is_recognised_by_either_marker() -> None:
    assert _activation(superseded_by="wf-9").is_superseded
    assert _activation(outcome=Outcome.SUPERSEDED).is_superseded
    assert not _activation(outcome=Outcome.DONE).is_superseded


def test_canonical_json_is_sorted_and_compact() -> None:
    assert canonical_json_bytes({"b": 1, "a": [1, 2]}) == b'{"a":[1,2],"b":1}'


def test_bead_record_ignores_unknown_bd_columns() -> None:
    record = BeadRecord.model_validate(
        {
            "id": "wf-1",
            "title": "t",
            "status": "open",
            "issue_type": "task",
            "metadata": {"wf_kind": "activation"},
            "dependent_count": 0,
        }
    )
    assert record.id == "wf-1"


def test_bound_setting_keys_are_scoped() -> None:
    assert (
        BoundSetting.MAX_ENTRIES.at("build-review") == "region.build-review.max_entries"
    )
    assert BoundSetting.MAX_TOTAL_ACTIVATIONS.at() == "instance.max_total_activations"


@pytest.mark.parametrize(
    ("key", "setting", "scope"),
    [
        ("instance.max_total_activations", BoundSetting.MAX_TOTAL_ACTIVATIONS, ""),
        ("region.build-review.max_entries", BoundSetting.MAX_ENTRIES, "build-review"),
        (
            "node.implement.max_infra_retries",
            BoundSetting.MAX_INFRA_RETRIES,
            "implement",
        ),
        ("node.review.max_steers", BoundSetting.MAX_STEERS, "review"),
    ],
)
def test_a_bound_key_round_trips_through_the_closed_vocabulary(
    key: str, setting: BoundSetting, scope: str
) -> None:
    parsed = parse_bound_key(key)
    assert parsed is not None
    assert parsed.setting is setting
    assert parsed.scope == scope
    assert setting.at(scope) == key


@pytest.mark.parametrize(
    "key",
    [
        "instance.max_total_activationsX",
        "region.build-review.max_steers",
        "anything",
        "node..max_steers",
        "region.a.b.max_entries",
    ],
)
def test_a_key_outside_the_bound_vocabulary_does_not_parse(key: str) -> None:
    # §9 restricts a rebudget to the closed set, so "unparseable" must be
    # distinguishable from "valid" — never coerced into the nearest match.
    assert parse_bound_key(key) is None


@pytest.mark.parametrize("value", [2**53, -(2**53), 2**63, 12345678901234567890])
def test_a_carrier_integer_beyond_json_precision_is_refused_before_the_write(
    value: int,
) -> None:
    # bd rounds these silently through its float64 JSON path (probed). The
    # read-back check catches it after the fact; the constraint prevents it.
    with pytest.raises(ValidationError):
        _activation(seq=value)
    with pytest.raises(ValidationError):
        Usage(known=True, input_tokens=value)


def test_json_safe_integers_at_the_boundary_are_accepted() -> None:
    assert _activation(seq=2**53 - 1).seq == 2**53 - 1


# --- request objects fail closed ----------------------------------------


def test_a_transition_gate_without_its_key_parts_is_refused() -> None:
    # Two transition gates whose keys fell back to defaults would hash alike.
    with pytest.raises(CarrierIntegrityError, match="source_activation_id"):
        GateOpenRequest(gate_node="ship", outcomes=(Outcome.APPROVE,))


def test_an_exhaustion_gate_needs_its_region_and_round() -> None:
    with pytest.raises(CarrierIntegrityError, match="region, round_no"):
        GateOpenRequest(
            gate_node="triage",
            outcomes=(Outcome.REBUDGET,),
            gate_reason=GateReason.EXHAUSTION,
        )


def test_a_halt_gate_states_why_it_halted() -> None:
    # §10.3: the reason is descriptive metadata, never a key part — keying on
    # it made the ceiling exemption unbounded. Metadata is not the same as
    # optional: the audit sweep reports why an instance halted.
    with pytest.raises(CarrierIntegrityError, match="halt_reason"):
        GateOpenRequest(
            gate_node="triage",
            outcomes=(Outcome.ABANDON,),
            gate_reason=GateReason.HALT,
        )
    request = GateOpenRequest(
        gate_node="triage",
        outcomes=(Outcome.ABANDON,),
        gate_reason=GateReason.HALT,
        halt_reason="ceiling",
    )
    assert request.halt_reason == "ceiling"


def test_a_mutable_gate_must_name_the_artifact_the_wrapper_will_re_hash() -> None:
    # Without a ref there is nothing to read, so the §9 freshness check would
    # be vacuous — the gate is refused at open, not silently unverifiable.
    with pytest.raises(CarrierIntegrityError, match="artifact_ref"):
        GateOpenRequest(
            gate_node="ship",
            outcomes=(Outcome.APPROVE,),
            source_activation_id="wf-1",
            opening_outcome=Outcome.ACCEPT,
            binds=BindsMode.MUTABLE,
        )
    accepted = GateOpenRequest(
        gate_node="ship",
        outcomes=(Outcome.APPROVE,),
        source_activation_id="wf-1",
        opening_outcome=Outcome.ACCEPT,
        binds=BindsMode.MUTABLE,
        artifact_ref="docs/plan.md",
        artifact_digest="a" * 64,
    )
    assert accepted.artifact_ref == "docs/plan.md"


@pytest.mark.parametrize(
    "field", ["region", "round_no", "outcome_taken", "intended_base_commit"]
)
def test_a_mint_request_cannot_state_a_fact_the_store_derives(field: str) -> None:
    # §3.2: region, round_no, outcome_taken and intended_base_commit are
    # derived from the pinned graph and the recorded trace. A caller able to
    # state them could dodge the bound that reads them.
    assert field not in MintRequest.model_fields
    with pytest.raises(ValidationError, match="extra_forbidden|Extra inputs"):
        MintRequest.model_validate(
            {
                "node": NODE,
                "mint_reason": MintReason.ENTRY,
                "runner_profile": "p",
                "model": "m",
                "session_id": "s",
                field: 1,
            }
        )


def test_gate_metadata_defaults_to_an_open_immutable_human_gate() -> None:
    gate = GateMetadata(
        wf_root_id=ROOT_ID,
        gate_key="gk",
        gate_node="ship",
        outcomes=(Outcome.APPROVE, Outcome.ABANDON),
        seq=2,
    )
    dumped = metadata_dict(gate)
    assert dumped["state"] == "open"
    assert dumped["binds"] == "immutable"
    assert dumped["wf_kind"] == WfKind.GATE.value


# --- keys ---------------------------------------------------------------


def test_idempotency_key_is_deterministic_and_input_sensitive() -> None:
    first = keys.idempotency_key(ROOT_ID, "wf-1", Outcome.REJECT, NODE)
    assert first == keys.idempotency_key(ROOT_ID, "wf-1", Outcome.REJECT, NODE)
    assert first != keys.idempotency_key(ROOT_ID, "wf-1", Outcome.DONE, NODE)
    assert first != keys.idempotency_key(ROOT_ID, "wf-2", Outcome.REJECT, NODE)
    assert first != keys.entry_idempotency_key(ROOT_ID)


def test_key_parts_are_separated_so_concatenation_cannot_collide() -> None:
    # ("ab", "c") and ("a", "bc") must not hash alike.
    assert keys.gate_key(ROOT_ID, "ab", "c", Outcome.APPROVE) != keys.gate_key(
        ROOT_ID, "a", "bc", Outcome.APPROVE
    )


def test_gate_key_domains_do_not_collide() -> None:
    same_parts = ("r", "region", "1")
    assert keys.exhaustion_gate_key("r", "region", 1) != keys.halt_gate_key("r", 1)
    assert keys.exhaustion_gate_key(*same_parts[:2], 1) != keys.gate_key(
        "r", "region", "1", Outcome.APPROVE
    )


def test_exhaustion_and_halt_gate_keys_are_stable_across_ticks() -> None:
    assert keys.exhaustion_gate_key(ROOT_ID, "build-review", 4) == (
        keys.exhaustion_gate_key(ROOT_ID, "build-review", 4)
    )
    assert keys.halt_gate_key(ROOT_ID, 0) == keys.halt_gate_key(ROOT_ID, 0)
    assert keys.halt_gate_key(ROOT_ID, 0) != keys.halt_gate_key("wf-other", 0)
    # §10.3: each halt gets its own bead, so the ordinal must move the key.
    assert keys.halt_gate_key(ROOT_ID, 0) != keys.halt_gate_key(ROOT_ID, 1)


def test_event_key_identifies_one_transition() -> None:
    first = keys.event_key(ROOT_ID, "wf-1", "implement", Outcome.DONE, "review")
    assert first == keys.event_key(ROOT_ID, "wf-1", "implement", Outcome.DONE, "review")
    assert first != keys.event_key(ROOT_ID, "wf-1", "implement", Outcome.DONE, "triage")
