"""Public task-cost seams over synthetic, local-only accounting data."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from tests._helpers import seeded_records
from workflow_interpreter.bdio.client import ISSUE_TYPE_OF, as_row
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.rows import RowQuery, StoreRow
from workflow_interpreter.bdio.wire import BeadRecord
from workflow_interpreter.contractor.models import ContractorRecord
from workflow_interpreter.contractor.records import LedgerContractorRecords
from workflow_interpreter.costs.collection import (
    CompletionEvidence,
    TaskCollection,
    collect_task,
)
from workflow_interpreter.costs.models import Measurement, TokenUsage, UsageObservation
from workflow_interpreter.costs.pricing import PriceBook, price_observations
from workflow_interpreter.costs.profiles import LogContext, parse_log
from workflow_interpreter.costs.report import (
    build_task_report,
    cohort_report,
    cohort_text_report,
    text_report,
)
from workflow_interpreter.costs.supplement import UsageSupplement, apply_supplement
from workflow_interpreter.ledger.database import open_ledger


def _pricebook() -> PriceBook:
    return PriceBook.model_validate(
        {
            "schema": "task-cost-pricebook/1",
            "currency": "USD",
            "snapshots": [
                {
                    "retrieved_at": "2026-09-13",
                    "sources": ["https://example.invalid/official"],
                    "rates": [
                        {
                            "model": "gpt-5.6-sol",
                            "provider": "openai",
                            "service_tier": "standard",
                            "mapping_provenance": "exact model id",
                            "per_million": {
                                "input": "4",
                                "cache_read": ".4",
                                "cache_write_5m": "9",
                                "cache_write_1h": None,
                                "output": "20",
                            },
                        }
                    ],
                }
            ],
        }
    )


def test_pricing_uses_exact_decimal_arithmetic_and_distinguishes_zero() -> None:
    observation = UsageObservation(
        identity="root/a/launch/turn",
        provider="openai",
        profile="codex",
        root_id="root",
        activation_id="a",
        launch_id="launch",
        session_id="session",
        event_id="turn",
        model="gpt-5.6-sol",
        service_tier="standard",
        measurement=Measurement.STEP_DELTA,
        tokens=TokenUsage(input=1, cache_read=2, output=3, cache_write=0),
        source="fixture.jsonl:2",
    )

    priced = price_observations((observation,), _pricebook(), as_of="2026-09-13")

    assert priced.known_subtotal_usd == Decimal("0.0000648")
    assert priced.complete is True
    assert priced.missing_rates == ()


@pytest.mark.parametrize("bad", [True, -1, 1.5, "1"])
def test_token_values_are_strict_nonnegative_integers(bad: object) -> None:
    with pytest.raises(ValidationError):
        TokenUsage(input=bad)  # type: ignore[arg-type]


def test_missing_usage_is_invalid_but_measured_zero_is_valid() -> None:
    common = {
        "identity": "identity",
        "provider": "openai",
        "profile": "codex",
        "root_id": "root",
        "activation_id": "activation",
        "event_id": "turn",
        "model": "gpt-5.6-sol",
        "measurement": "step-delta",
        "source": "fixture",
    }

    with pytest.raises(ValidationError):
        UsageObservation.model_validate(common | {"tokens": {}})
    measured = UsageObservation.model_validate(common | {"tokens": {"input": 0}})

    assert measured.tokens.input == 0


def test_missing_token_categories_make_pricing_incomplete() -> None:
    observation = UsageObservation(
        identity="partial",
        provider="openai",
        profile="codex",
        root_id="root",
        activation_id="activation",
        event_id="turn",
        model="gpt-5.6-sol",
        service_tier="standard",
        measurement=Measurement.STEP_DELTA,
        tokens=TokenUsage(input=1, cache_read=0, output=None, cache_write=0),
        source="fixture",
    )

    priced = price_observations((observation,), _pricebook())

    assert priced.complete is False
    assert priced.known_subtotal_usd == Decimal("0.000004")
    assert priced.missing_usage == ("partial:output",)


def test_cache_write_total_and_ttl_buckets_are_mutually_exclusive() -> None:
    with pytest.raises(ValidationError, match="cache write"):
        TokenUsage(cache_write=3, cache_write_5m=1, cache_write_1h=2)


def test_pricebook_rejects_nonfinite_money() -> None:
    raw = _pricebook().model_dump(mode="json", by_alias=True)
    raw["snapshots"][0]["rates"][0]["per_million"]["input"] = "NaN"

    with pytest.raises(ValidationError):
        PriceBook.model_validate(raw)


def test_generic_cache_write_never_assumes_a_ttl_rate() -> None:
    observation = UsageObservation(
        identity="root/a/launch/turn",
        provider="openai",
        profile="codex",
        root_id="root",
        activation_id="a",
        launch_id="launch",
        session_id="session",
        event_id="turn",
        model="gpt-5.6-sol",
        measurement=Measurement.STEP_DELTA,
        tokens=TokenUsage(cache_write=1),
        source="fixture.jsonl:2",
    )

    priced = price_observations((observation,), _pricebook())

    assert priced.known_subtotal_usd == 0
    assert priced.complete is False
    assert priced.missing_rates == ("root/a/launch/turn:cache_write",)


def test_unknown_service_tier_requires_explicit_standard_normalization() -> None:
    observation = UsageObservation(
        identity="root/a/durable",
        provider="openai",
        profile="codex",
        root_id="root",
        activation_id="a",
        exec_id="a",
        session_id="session",
        model="gpt-5.6-sol",
        measurement=Measurement.TERMINAL_CUMULATIVE,
        tokens=TokenUsage(input=1, cache_read=0, cache_write=0, output=1),
        source="bd:a",
    )

    unknown = price_observations((observation,), _pricebook())
    normalized = price_observations(
        (observation,), _pricebook(), normalize_standard=True
    )

    assert unknown.complete is False
    assert unknown.known_subtotal_usd == 0
    assert normalized.complete is True
    assert normalized.known_subtotal_usd == Decimal("0.000024")
    assert normalized.pricing_basis == "standard-rate-normalization"


def test_pricebook_round_trip_fixture_is_strict(tmp_path: Path) -> None:
    path = tmp_path / "prices.json"
    path.write_text(json.dumps(_pricebook().model_dump(mode="json", by_alias=True)))

    assert PriceBook.load(path).snapshots[0].retrieved_at.isoformat() == "2026-09-13"


def test_explicit_as_of_reprices_against_the_named_snapshot() -> None:
    latest = _pricebook().model_dump(mode="json", by_alias=True)["snapshots"][0]
    historical = json.loads(json.dumps(latest))
    historical["retrieved_at"] = "2025-01-01"
    historical["rates"][0]["per_million"]["input"] = "2"
    book = PriceBook.model_validate(
        {
            "schema": "task-cost-pricebook/1",
            "currency": "USD",
            "snapshots": [historical, latest],
        }
    )
    observation = UsageObservation(
        identity="dated",
        provider="openai",
        profile="codex",
        root_id="root",
        activation_id="activation",
        event_id="turn",
        model="gpt-5.6-sol",
        service_tier="standard",
        measurement=Measurement.STEP_DELTA,
        tokens=TokenUsage(input=1_000_000),
        source="fixture",
    )

    old = price_observations((observation,), book, as_of="2025-01-01")
    current = price_observations((observation,), book, as_of="2026-09-13")

    assert old.known_subtotal_usd == 2
    assert current.known_subtotal_usd == 4


def test_observation_duplicates_dedupe_and_conflicts_fail() -> None:
    observation = UsageObservation(
        identity="same",
        provider="openai",
        profile="codex",
        root_id="root",
        activation_id="activation",
        event_id="turn",
        model="gpt-5.6-sol",
        service_tier="standard",
        measurement=Measurement.STEP_DELTA,
        tokens=TokenUsage(input=1),
        source="fixture",
    )

    exact = price_observations((observation, observation), _pricebook())

    assert len(exact.observations) == 1
    with pytest.raises(ValueError, match="conflicting usage identity"):
        price_observations(
            (
                observation,
                observation.model_copy(update={"tokens": TokenUsage(input=2)}),
            ),
            _pricebook(),
        )


def test_codex_terminal_turn_subtracts_cached_input_and_not_reasoning(
    tmp_path: Path,
) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        '{"type":"thread.started","thread_id":"session-1"}\n'
        '{"type":"turn.completed","turn_id":"turn-1","usage":'
        '{"input_tokens":100,"cached_input_tokens":80,'
        '"cache_write_input_tokens":0,"output_tokens":20,'
        '"reasoning_output_tokens":7}}\n'
    )

    parsed = parse_log(
        path,
        LogContext(
            profile="codex",
            root_id="root-1",
            activation_id="activation-1",
            launch_id="launch-1",
            requested_model="gpt-5.6-sol",
            model="gpt-5.6-sol",
            role="critic",
        ),
    )

    assert parsed.complete is True
    assert len(parsed.observations) == 1
    assert parsed.observations[0].tokens == TokenUsage(
        input=20, cache_read=80, cache_write=0, output=20, reasoning=7
    )


def test_claude_model_usage_avoids_double_counting_top_level_totals(
    tmp_path: Path,
) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "result",
                "uuid": "result-1",
                "session_id": "session-1",
                "result": "SECRET TRANSCRIPT MUST NEVER APPEAR",
                "usage": {
                    "input_tokens": 3,
                    "cache_read_input_tokens": 5,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 7,
                    "service_tier": "standard",
                },
                "modelUsage": {
                    "claude-opus-5": {
                        "inputTokens": 3,
                        "cacheReadInputTokens": 5,
                        "cacheCreationInputTokens": 0,
                        "outputTokens": 7,
                        "thinkingTokens": 2,
                        "costUSD": 0.01,
                        "canonicalModel": "claude-opus-5-canonical",
                    },
                    "claude-haiku-4-5": {
                        "inputTokens": 11,
                        "cacheReadInputTokens": 0,
                        "cacheCreationInputTokens": 0,
                        "outputTokens": 13,
                        "thinkingTokens": 0,
                        "costUSD": 0.02,
                    },
                },
            }
        )
        + "\n"
    )

    parsed = parse_log(
        path,
        LogContext(
            profile="claude",
            root_id="root-1",
            activation_id="activation-1",
            launch_id="launch-1",
            requested_model="claude-opus-5",
            model="claude-opus-5",
            role="implementer",
        ),
    )

    assert [item.model for item in parsed.observations] == [
        "claude-haiku-4-5",
        "claude-opus-5",
    ]
    assert sum(item.tokens.output or 0 for item in parsed.observations) == 20
    assert parsed.observations[1].requested_model == "claude-opus-5"
    assert parsed.observations[1].observed_model == "claude-opus-5-canonical"
    assert "modelUsage key" in (parsed.observations[1].model_mapping_provenance or "")
    assert parsed.observations[0].service_tier is None
    assert parsed.observations[1].service_tier == "standard"
    assert "SECRET" not in parsed.model_dump_json()


def test_malformed_and_oversized_logs_are_safe_and_incomplete(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text('{"type":"turn.completed","secret":"DO NOT LEAK"}\n{torn')
    context = LogContext(
        profile="codex",
        root_id="root-1",
        activation_id="activation-1",
        launch_id="launch-1",
        requested_model="gpt-5.6-sol",
        model="gpt-5.6-sol",
        role="critic",
    )

    malformed = parse_log(path, context)
    oversized = parse_log(path, context, max_bytes=5)

    assert malformed.complete is False
    assert {item.code for item in malformed.diagnostics} == {
        "malformed-json",
        "usage-event-invalid",
    }
    assert oversized.diagnostics[0].code == "log-too-large"
    assert "DO NOT LEAK" not in malformed.model_dump_json()


class FakeReadClient:
    """Minimal local BdClient-shaped read seam with no mutation surface."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = {str(row["id"]): row for row in rows}
        self.reads: list[str] = []

    def show(self, bead_id: str) -> BeadRecord:
        """Return one synthetic bead."""
        self.reads.append(f"show:{bead_id}")
        return BeadRecord.model_validate(self.rows[bead_id])

    def list_beads(self, *, metadata_filters=None, issue_type=None):
        """Return rows matching the same metadata conjunction as BdClient."""
        self.reads.append("list")
        selected = []
        for raw in self.rows.values():
            if issue_type is not None and raw["issue_type"] != issue_type.value:
                continue
            metadata = raw.get("metadata", {})
            if all(
                metadata.get(key) == value
                for key, value in (metadata_filters or {}).items()
            ):
                selected.append(BeadRecord.model_validate(raw))
        return tuple(selected)

    def find_rows(self, query: RowQuery) -> tuple[StoreRow, ...]:
        """The neutral read the §4 vocabulary issues, over the same rows."""
        return tuple(
            as_row(record)
            for record in self.list_beads(
                metadata_filters=query.metadata_filters,
                issue_type=None if query.kind is None else ISSUE_TYPE_OF[query.kind],
            )
        )


def _collect(
    client, stage_id: str, *, record: dict[str, object] | None = None, **kwargs
):
    """Collect one stage with the roots served by the same synthetic rows.

    The backend factory is what production injects (§3.2); these rows stand in
    for BOTH the task bead and its roots, so the factory answers with the one
    client whichever backend the contractor record pins.

    `record` is the stage's contractor record. Handed in as JSON because that
    is how `collect_task` takes it since S4: the record is a ledger row (§3.2,
    R4), and the CLI that opens the read-only ledger is what reads it — so
    these cases state it directly rather than hiding it in a bead's metadata.
    """
    return collect_task(
        client,
        stage_id,
        backends=lambda _: client,
        record_json=json.dumps(_record() if record is None else record),
        **kwargs,
    )


def _record(*, current_root_id: str = "root-2") -> dict[str, object]:
    """The stage's contractor record, at the last state a finish leaves it.

    LANDED, not closed: nothing writes CLOSED since S2 and the member is gone
    since S4 — closure is derived from the ledger and its git anchor (§3.5).
    """
    oid = "a" * 40
    return {
        "schema": "contract/3",
        "state": "landed",
        "epic_id": "epic-1",
        "stage_id": "stage-1",
        "attempt": 2,
        "instance_key": "contract:epic-1:stage-1:attempt:2",
        "target_ref": "refs/heads/main",
        "expected_base_commit": oid,
        "root_id": current_root_id,
        "landed_oid": oid,
        "tree": "b" * 40,
        "gate_receipt_digest": "gate-digest",
        "landing_receipt_digest": "landing-digest",
        "previous_attempts": ["contract:epic-1:stage-1:attempt:1"],
    }


def _task_rows(*, closed: bool = True):
    oid = "a" * 40
    rows: list[dict[str, object]] = [
        {
            "id": "stage-1",
            "title": "stage",
            "status": "closed" if closed else "in_progress",
            "issue_type": "task",
            "metadata": {},
        }
    ]
    for root_id, attempt in (("root-1", 1), ("root-2", 2)):
        instance_key = f"contract:epic-1:stage-1:attempt:{attempt}"
        rows.append(
            {
                "id": root_id,
                "title": "root",
                "status": "closed",
                "issue_type": "task",
                "metadata": {
                    "wf_kind": "root",
                    "wf_root_id": root_id,
                    "instance_key": instance_key,
                },
            }
        )
        rows.append(
            {
                "id": f"activation-{attempt}",
                "title": "activation",
                "status": "closed",
                "issue_type": "task",
                "metadata": {
                    "wf_kind": "activation",
                    "wf_root_id": root_id,
                    "node": "implement" if attempt == 1 else "review",
                    "round_no": attempt,
                    "seq": 1,
                    "idempotency_key": f"key-{attempt}",
                    "mint_reason": "entry",
                    "crew_profile": "codex",
                    "model": "gpt-5.6-sol",
                    "session_id": f"session-{attempt}",
                    "intended_base_commit": oid,
                    "lifecycle": "closed",
                    "outcome": "fail_code" if attempt == 1 else "accept",
                    "handle": {
                        "pid": 100 + attempt,
                        "pgid": 100 + attempt,
                        "host": "fixture",
                        "host_boot_id": "boot",
                        "proc_start_time": str(attempt),
                        "started_at": f"2026-09-13T00:0{attempt}:00Z",
                        "log_path": "fixture-run.jsonl",
                        "session_id": f"session-{attempt}",
                    },
                    "exit_record": {
                        "exit_code": 0,
                        "ended_at": f"2026-09-13T00:0{attempt + 1}:00Z",
                        "reason": "exited",
                    },
                    "usage": {
                        "known": True,
                        "input_tokens": 10 * attempt,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 5 * attempt,
                        "cost_usd": f"0.0{attempt}",
                    },
                },
            }
        )
    return rows


def test_collection_includes_failed_and_successful_attempts_without_writes() -> None:
    client = FakeReadClient(_task_rows())

    collected = _collect(client, "stage-1")

    assert collected.completion.verified is True
    assert [root.root_id for root in collected.roots] == ["root-1", "root-2"]
    assert [item.activation_id for item in collected.activations] == [
        "activation-1",
        "activation-2",
    ]
    assert sum(item.tokens.output or 0 for item in collected.observations) == 15
    assert set(client.reads) <= {"show:stage-1", "list"}


def test_minted_activation_that_never_executed_does_not_degrade_usage_coverage() -> (
    None
):
    rows = _task_rows()
    metadata = rows[2]["metadata"]
    metadata["lifecycle"] = "minted"
    for field in ("handle", "exit_record", "outcome", "usage"):
        metadata.pop(field)

    collected = _collect(FakeReadClient(rows), "stage-1")

    assert collected.usage_complete is True
    assert [item.activation_id for item in collected.observations] == ["activation-2"]
    assert "usage-unreported" not in {item.code for item in collected.diagnostics}


@pytest.mark.parametrize(
    ("current_root_id", "closed"),
    [("forged-root", True), ("root-2", False)],
)
def test_completion_refuses_forged_or_merely_closed_evidence(
    current_root_id: str, closed: bool
) -> None:
    collected = _collect(
        FakeReadClient(_task_rows(closed=closed)),
        "stage-1",
        record=_record(current_root_id=current_root_id),
    )

    assert collected.completion.verified is False
    assert collected.coverage_complete is False


@pytest.mark.parametrize(
    "missing_field",
    ["landed_oid", "tree", "gate_receipt_digest", "landing_receipt_digest"],
)
def test_completion_requires_every_landing_field(missing_field: str) -> None:
    record = _record()
    record[missing_field] = None

    collected = _collect(FakeReadClient(_task_rows()), "stage-1", record=record)

    assert collected.completion.verified is False


def test_completion_rejects_mismatched_root_self_identity() -> None:
    rows = _task_rows()
    rows[1]["metadata"]["wf_root_id"] = "different-root"

    collected = _collect(FakeReadClient(rows), "stage-1")

    assert collected.completion.verified is False
    assert "root-identity-mismatch" in {item.code for item in collected.diagnostics}


def test_completion_rejects_duplicate_root_resolution() -> None:
    rows = _task_rows()
    duplicate = json.loads(json.dumps(rows[1]))
    duplicate["id"] = "root-duplicate"
    duplicate["metadata"]["wf_root_id"] = "root-duplicate"
    rows.append(duplicate)

    collected = _collect(FakeReadClient(rows), "stage-1")

    assert collected.completion.verified is False
    assert "root-resolution-ambiguous" in {item.code for item in collected.diagnostics}


@pytest.mark.parametrize(
    ("status", "terminal"),
    [("open", "shipped"), ("closed", "failed")],
)
def test_completion_rejects_current_root_terminal_contradictions(
    status: str, terminal: str
) -> None:
    rows = _task_rows()
    rows[3]["status"] = status
    rows[3]["metadata"]["terminal"] = terminal

    collected = _collect(FakeReadClient(rows), "stage-1")

    assert collected.completion.verified is False
    assert "current-root-terminal-contradiction" in {
        item.code for item in collected.diagnostics
    }


def test_completion_rejects_stage_close_reason_contradiction() -> None:
    rows = _task_rows()
    rows[0]["close_reason"] = "contractor landing receipt=different-digest"

    collected = _collect(FakeReadClient(rows), "stage-1")

    assert collected.completion.verified is False
    assert "stage-close-reason-contradiction" in {
        item.code for item in collected.diagnostics
    }


def test_completion_rejects_available_landing_record_contradiction(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "root-2"
    runtime_root.mkdir()
    contractor = _record()
    oid = str(contractor["landed_oid"])
    tree = str(contractor["tree"])
    intent = {
        "schema": "contract-landing/2",
        "ref": contractor["target_ref"],
        "expected_base": contractor["expected_base_commit"],
        "artifact_oid": oid,
        "tree": tree,
        "gate_receipt_digest": contractor["gate_receipt_digest"],
        "root_id": "root-2",
        "policy_digest": "policy",
        "stage": "stage-1",
        "attempt": 2,
    }
    receipt = {
        "intent_digest": "not-the-intent-digest",
        "ref": contractor["target_ref"],
        "expected_base": contractor["expected_base_commit"],
        "signed_oid": oid,
        "landed_oid": "c" * 40,
        "tree": tree,
        "gate_receipt_digest": contractor["gate_receipt_digest"],
        "policy_digest": "policy",
        "repository_gate_results": [
            {
                "name": "check",
                "command": {"name": "check", "argv": ["true"]},
                "executable_digest": "d" * 64,
                "exit_code": 0,
                "source_unchanged": True,
            }
        ],
    }
    (runtime_root / "contract-landing.json").write_text(json.dumps(intent))
    (runtime_root / "contract-landing-receipt.json").write_text(json.dumps(receipt))

    collected = _collect(
        FakeReadClient(_task_rows()),
        "stage-1",
        runtime_roots={"root-2": runtime_root},
    )

    assert collected.completion.verified is False
    assert "landing-evidence-contradiction" in {
        item.code for item in collected.diagnostics
    }


def test_task_report_is_partial_without_explicit_external_attribution() -> None:
    collected = _collect(FakeReadClient(_task_rows()), "stage-1")

    report = build_task_report(collected, _pricebook(), normalize_standard=True)

    assert report.cost_basis == "partial-observed-spend"
    assert report.whole_task_cost_usd is None
    assert report.known_priced_subtotal_usd == Decimal("0.00042")
    assert report.uncovered_scope
    assert report.raw_tokens.input == 30
    assert report.raw_tokens.output == 15
    assert [(item.role, item.model) for item in report.role_model_subtotals] == [
        ("implement", "gpt-5.6-sol"),
        ("review", "gpt-5.6-sol"),
    ]
    assert report.vendor_reported_cost_total_usd == Decimal("0.03")
    assert [item.seconds for item in report.measurable_durations] == [
        Decimal(60),
        Decimal(60),
    ]


def test_task_text_labels_explicit_as_of_as_api_estimate() -> None:
    report = build_task_report(
        _collect(FakeReadClient(_task_rows()), "stage-1"),
        _pricebook(),
        as_of="2026-09-13",
    )

    rendered = text_report(report)

    assert report.price_snapshot_selection == "explicit-as-of"
    assert (
        "cost interpretation: API-equivalent estimate; not actual billing" in rendered
    )
    assert "pricing basis: observed-tier" in rendered
    assert "price snapshot: explicit-as-of (2026-09-13)" in rendered


def test_task_report_aggregates_generic_and_ttl_cache_write_representations() -> None:
    common = {
        "provider": "openai",
        "profile": "codex",
        "root_id": "root",
        "role": "implement",
        "model": "gpt-5.6-sol",
        "service_tier": "standard",
        "measurement": Measurement.STEP_DELTA,
        "source": "fixture",
    }
    generic = UsageObservation(
        **common,
        identity="generic",
        activation_id="activation-1",
        event_id="turn-1",
        tokens=TokenUsage(input=1, cache_read=0, cache_write=2, output=1),
    )
    ttl_split = UsageObservation(
        **common,
        identity="ttl-split",
        activation_id="activation-2",
        event_id="turn-2",
        tokens=TokenUsage(
            input=3,
            cache_read=0,
            cache_write_5m=4,
            cache_write_1h=5,
            output=2,
        ),
    )
    collection = TaskCollection(
        task_id="stage",
        epic_id="epic",
        completion=CompletionEvidence(verified=True, basis=("fixture:valid",)),
        roots=(),
        activations=(),
        observations=(generic, ttl_split),
        diagnostics=(),
        uncovered_scope=(),
        usage_complete=True,
        coverage_complete=True,
    )

    report = build_task_report(collection, _pricebook())

    assert report.raw_tokens.cache_write == 2
    assert report.raw_tokens.cache_write_5m == 4
    assert report.raw_tokens.cache_write_1h == 5
    assert report.role_model_subtotals[0].tokens == report.raw_tokens


def test_strict_supplement_supplies_usage_and_explicit_coverage_basis() -> None:
    raw = {
        "schema": "task-cost-supplement/1",
        "records": [
            {
                "record_id": "record-1",
                "usage_identity": "external/session/turn-1",
                "owner_task_id": "stage-1",
                "parent_task_id": None,
                "source_reference": "operator-ledger:1",
                "provider": "openai",
                "profile": "codex",
                "model": "gpt-5.6-sol",
                "service_tier": "standard",
                "measurement": "step-delta",
                "role": "coordinator",
                "effort": "high",
                "tokens": {
                    "input": 5,
                    "cache_read": 0,
                    "cache_write": 0,
                    "output": 1,
                },
            }
        ],
        "scope_declarations": [
            {
                "task_id": "stage-1",
                "source_reference": "operator-ledger:coverage",
                "coordinator_complete": True,
                "children_complete": True,
            }
        ],
    }
    supplement = UsageSupplement.model_validate(raw)
    collected = apply_supplement(
        _collect(FakeReadClient(_task_rows()), "stage-1"), supplement
    )

    report = build_task_report(collected, _pricebook(), normalize_standard=True)

    assert report.cost_basis == "whole-task"
    assert report.whole_task_cost_usd == Decimal("0.00046")
    assert report.uncovered_scope == ()


def test_complete_external_declaration_preserves_unreadable_task_scope() -> None:
    collected = _collect(
        FakeReadClient(_task_rows()), "stage-1", record={"invalid": "identity"}
    )
    supplemented = apply_supplement(
        collected,
        UsageSupplement.model_validate(
            {
                "schema": "task-cost-supplement/1",
                "records": [],
                "scope_declarations": [
                    {
                        "task_id": "stage-1",
                        "source_reference": "operator-ledger:coverage",
                        "coordinator_complete": True,
                        "children_complete": True,
                    }
                ],
            }
        ),
    )

    report = build_task_report(supplemented, _pricebook())
    rendered = text_report(report)

    assert supplemented.uncovered_scope == ("task execution identity is unavailable",)
    assert supplemented.diagnostics == collected.diagnostics
    assert supplemented.coverage_complete is False
    assert "uncovered scope: task execution identity is unavailable" in rendered
    assert "diagnostic: contract-invalid: contractor record is invalid" in rendered


def test_supplement_exact_duplicates_dedupe_and_conflicts_fail() -> None:
    record = {
        "record_id": "record-1",
        "usage_identity": "external/session/turn-1",
        "owner_task_id": "stage-1",
        "source_reference": "operator-ledger:1",
        "provider": "openai",
        "profile": "codex",
        "model": "gpt-5.6-sol",
        "service_tier": "standard",
        "measurement": "step-delta",
        "role": "coordinator",
        "tokens": {"input": 5, "output": 1},
    }
    exact = UsageSupplement.model_validate(
        {
            "schema": "task-cost-supplement/1",
            "records": [record, record],
            "scope_declarations": [],
        }
    )
    assert len(exact.records_for("stage-1")) == 1
    with pytest.raises(ValueError, match="conflicting supplement record_id"):
        UsageSupplement.model_validate(
            {
                "schema": "task-cost-supplement/1",
                "records": [
                    record,
                    record | {"tokens": {"input": 6, "output": 1}},
                ],
                "scope_declarations": [],
            }
        )


def test_cohort_separates_failure_spend_and_zero_completion_nulls() -> None:
    complete = build_task_report(
        apply_supplement(
            _collect(FakeReadClient(_task_rows()), "stage-1"),
            UsageSupplement.model_validate(
                {
                    "schema": "task-cost-supplement/1",
                    "records": [],
                    "scope_declarations": [
                        {
                            "task_id": "stage-1",
                            "source_reference": "operator-ledger:coverage",
                            "coordinator_complete": True,
                            "children_complete": True,
                        }
                    ],
                }
            ),
        ),
        _pricebook(),
        normalize_standard=True,
    )
    incomplete = build_task_report(
        _collect(FakeReadClient(_task_rows(closed=False)), "stage-1"),
        _pricebook(),
        normalize_standard=True,
    )
    incomplete = incomplete.model_copy(
        update={
            "task_id": "stage-2",
            "priced_usage": tuple(
                item.model_copy(
                    update={
                        "observation": item.observation.model_copy(
                            update={"identity": f"stage-2/{item.observation.identity}"}
                        )
                    }
                )
                for item in incomplete.priced_usage
            ),
        }
    )

    cohort = cohort_report((complete, incomplete))
    empty = cohort_report((incomplete,))

    assert cohort.completed_task_cost_denominator == 1
    assert cohort.mean_completed_task_cost_usd == Decimal("0.00042")
    assert cohort.total_observed_spend_usd == Decimal("0.00084")
    assert cohort.success_rate == Decimal("0.5")
    assert empty.mean_completed_task_cost_usd is None


def test_cohort_unions_parent_child_supplement_usage_identity() -> None:
    complete = build_task_report(
        apply_supplement(
            _collect(FakeReadClient(_task_rows()), "stage-1"),
            UsageSupplement.model_validate(
                {
                    "schema": "task-cost-supplement/1",
                    "records": [],
                    "scope_declarations": [
                        {
                            "task_id": "stage-1",
                            "source_reference": "operator-ledger:coverage",
                            "coordinator_complete": True,
                            "children_complete": True,
                        }
                    ],
                }
            ),
        ),
        _pricebook(),
        normalize_standard=True,
    )
    shared = complete.priced_usage[0]
    child = complete.model_copy(
        update={
            "task_id": "child-1",
            "priced_usage": (shared,),
            "known_priced_subtotal_usd": shared.known_cost_usd,
            "whole_task_cost_usd": shared.known_cost_usd,
        }
    )

    cohort = cohort_report((complete, child))

    assert cohort.total_observed_spend_usd == complete.known_priced_subtotal_usd


def test_mixed_pricing_basis_is_explicit_in_cohort_json_and_text() -> None:
    collected = apply_supplement(
        _collect(FakeReadClient(_task_rows()), "stage-1"),
        UsageSupplement.model_validate(
            {
                "schema": "task-cost-supplement/1",
                "records": [],
                "scope_declarations": [
                    {
                        "task_id": "stage-1",
                        "source_reference": "operator-ledger:coverage",
                        "coordinator_complete": True,
                        "children_complete": True,
                    }
                ],
            }
        ),
    )
    observed_collection = collected.model_copy(
        update={
            "observations": tuple(
                item.model_copy(update={"service_tier": "standard"})
                for item in collected.observations
            )
        }
    )
    observed = build_task_report(observed_collection, _pricebook())
    normalized = build_task_report(collected, _pricebook(), normalize_standard=True)
    normalized = normalized.model_copy(
        update={
            "task_id": "stage-2",
            "priced_usage": tuple(
                item.model_copy(
                    update={
                        "observation": item.observation.model_copy(
                            update={"identity": f"stage-2/{item.observation.identity}"}
                        )
                    }
                )
                for item in normalized.priced_usage
            ),
        }
    )

    cohort = cohort_report((observed, normalized))
    payload = json.loads(cohort.model_dump_json())
    rendered = cohort_text_report(cohort)

    assert payload["pricing_basis"] == "mixed"
    assert payload["completed_cost_statistics_pricing_basis"] == "mixed"
    assert payload["total_observed_spend_pricing_basis"] == "mixed"
    assert payload["price_snapshot_selection"] == "latest-available"
    assert payload["pricebook_dates"] == ["2026-09-13"]
    assert (
        "cost interpretation: API-equivalent estimate; not actual billing" in rendered
    )
    assert "completed cost statistics pricing basis: mixed" in rendered
    assert "total observed spend pricing basis: mixed" in rendered
    assert "price snapshot: latest-available (2026-09-13)" in rendered


def test_claude_unambiguous_cache_creation_splits_ttls(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "result",
                "uuid": "result-1",
                "session_id": "session-1",
                "usage": {
                    "input_tokens": 1,
                    "cache_read_input_tokens": 2,
                    "cache_creation_input_tokens": 7,
                    "cache_creation": {
                        "ephemeral_5m_input_tokens": 3,
                        "ephemeral_1h_input_tokens": 4,
                    },
                    "output_tokens": 5,
                },
            }
        )
        + "\n"
    )
    parsed = parse_log(
        path,
        LogContext(
            profile="claude",
            root_id="root",
            activation_id="activation",
            launch_id="launch",
            requested_model="claude-opus-5",
            model="claude-opus-5",
            role="implementer",
        ),
    )

    assert parsed.observations[0].tokens.cache_write is None
    assert parsed.observations[0].tokens.cache_write_5m == 3
    assert parsed.observations[0].tokens.cache_write_1h == 4


def test_multiple_claude_terminal_results_are_incomplete(tmp_path: Path) -> None:
    event = {
        "type": "result",
        "session_id": "same-session",
        "usage": {
            "input_tokens": 1,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 1,
        },
    }
    path = tmp_path / "run.jsonl"
    path.write_text(
        json.dumps(event | {"uuid": "one"})
        + "\n"
        + json.dumps(event | {"uuid": "two"})
        + "\n"
    )

    parsed = parse_log(
        path,
        LogContext(
            profile="claude",
            root_id="root",
            activation_id="activation",
            launch_id="launch",
            requested_model="claude-opus-5",
            model="claude-opus-5",
            role="implementer",
        ),
    )

    assert parsed.complete is False
    assert parsed.observations == ()
    assert parsed.diagnostics[0].code == "cumulative-boundary-ambiguous"


def test_codex_turn_totals_are_independent_deltas_across_counter_reset(
    tmp_path: Path,
) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        '{"type":"thread.started","thread_id":"session"}\n'
        '{"type":"turn.completed","turn_id":"one","usage":'
        '{"input_tokens":100,"cached_input_tokens":80,'
        '"cache_write_input_tokens":0,"output_tokens":20}}\n'
        '{"type":"turn.completed","turn_id":"two","usage":'
        '{"input_tokens":10,"cached_input_tokens":5,'
        '"cache_write_input_tokens":0,"output_tokens":2}}\n'
    )
    parsed = parse_log(
        path,
        LogContext(
            profile="codex",
            root_id="root",
            activation_id="activation",
            launch_id="launch",
            requested_model="gpt-5.6-sol",
            model="gpt-5.6-sol",
            role="critic",
        ),
    )

    assert parsed.complete is True
    assert [item.tokens.input for item in parsed.observations] == [20, 5]


def test_runtime_mapping_refuses_missing_root_without_raising(tmp_path: Path) -> None:
    collected = _collect(
        FakeReadClient(_task_rows()),
        "stage-1",
        runtime_roots={"root-1": tmp_path / "absent"},
    )

    assert collected.coverage_complete is False
    assert "runtime-path-invalid" in {item.code for item in collected.diagnostics}
    assert [item.activation_id for item in collected.observations].count(
        "activation-1"
    ) == 1


def test_runtime_mapping_never_reads_a_symlink_escape(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    activation_dir = runtime_root / "activation-1"
    activation_dir.mkdir(parents=True)
    outside = tmp_path / "outside.jsonl"
    outside.write_text(
        '{"type":"turn.completed","turn_id":"stolen","usage":'
        '{"input_tokens":9,"cached_input_tokens":0,'
        '"cache_write_input_tokens":0,"output_tokens":9}}\n'
    )
    (activation_dir / "run.jsonl").symlink_to(outside)
    (activation_dir / "launch-receipt.json").write_text("{}")

    collected = _collect(
        FakeReadClient(_task_rows()),
        "stage-1",
        runtime_roots={"root-1": runtime_root},
    )

    assert not [item for item in collected.observations if item.event_id == "stolen"]
    assert "runtime-path-invalid" in {item.code for item in collected.diagnostics}


def _write_valid_runtime_activation(
    runtime_root: Path, *, run_log: str | None = None
) -> Path:
    activation_dir = runtime_root / "activation-1"
    activation_dir.mkdir(parents=True)
    (activation_dir / "run.jsonl").write_text(
        run_log
        or (
            '{"type":"thread.started","thread_id":"session-1"}\n'
            '{"type":"turn.completed","turn_id":"turn-1","usage":'
            '{"input_tokens":9,"cached_input_tokens":0,'
            '"cache_write_input_tokens":0,"output_tokens":9}}\n'
        )
    )
    (activation_dir / "launch-receipt.json").write_text(
        json.dumps(
            {
                "launch_id": "launch-1",
                "root_id": "root-1",
                "activation_id": "activation-1",
                "argv": ["codex"],
                "cwd": "/repo",
                "handle": {
                    "pid": 1,
                    "pgid": 1,
                    "host": "fixture",
                    "host_boot_id": "boot",
                    "proc_start_time": "1",
                    "started_at": "2026-09-13T00:00:00Z",
                    "log_path": "run.jsonl",
                    "session_id": "session-1",
                },
                "sandbox": "off",
            }
        )
    )
    (activation_dir / "exec.ledger").write_text(
        json.dumps(
            {
                "launch_id": "launch-1",
                "activation_id": "activation-1",
                "pid": 1,
                "at": "2026-09-13T00:00:00Z",
            }
        )
        + "\n"
    )
    return activation_dir


def test_supplement_cannot_hide_incomplete_raw_telemetry(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    _write_valid_runtime_activation(
        runtime_root,
        run_log='{"type":"system","session_id":"session-1"}\n',
    )
    rows = _task_rows()
    rows[2]["metadata"]["crew_profile"] = "claude"
    rows[2]["metadata"]["model"] = "claude-opus-5"
    collected = _collect(
        FakeReadClient(rows),
        "stage-1",
        runtime_roots={"root-1": runtime_root},
    )
    supplemented = apply_supplement(
        collected,
        UsageSupplement.model_validate(
            {
                "schema": "task-cost-supplement/1",
                "records": [],
                "scope_declarations": [
                    {
                        "task_id": "stage-1",
                        "source_reference": "operator-ledger:coverage",
                        "coordinator_complete": True,
                        "children_complete": True,
                    }
                ],
            }
        ),
    )

    assert collected.usage_complete is False
    assert supplemented.coverage_complete is False


def test_runtime_mapping_refuses_an_oversized_exec_ledger(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    activation_dir = _write_valid_runtime_activation(runtime_root)
    (activation_dir / "exec.ledger").write_text(" " * 513)

    collected = _collect(
        FakeReadClient(_task_rows()),
        "stage-1",
        runtime_roots={"root-1": runtime_root},
        max_log_bytes=512,
    )

    assert not [item for item in collected.observations if item.event_id == "turn-1"]
    assert "exec-ledger-invalid" in {item.code for item in collected.diagnostics}


def test_runtime_mapping_never_reads_an_exec_ledger_symlink_escape(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    activation_dir = runtime_root / "activation-1"
    activation_dir.mkdir(parents=True)
    (activation_dir / "run.jsonl").write_text(
        '{"type":"thread.started","thread_id":"session-1"}\n'
        '{"type":"turn.completed","turn_id":"turn-1","usage":'
        '{"input_tokens":9,"cached_input_tokens":0,'
        '"cache_write_input_tokens":0,"output_tokens":9}}\n'
    )
    (activation_dir / "launch-receipt.json").write_text(
        json.dumps(
            {
                "launch_id": "launch-1",
                "root_id": "root-1",
                "activation_id": "activation-1",
                "argv": ["codex"],
                "cwd": "/repo",
                "handle": {
                    "pid": 1,
                    "pgid": 1,
                    "host": "fixture",
                    "host_boot_id": "boot",
                    "proc_start_time": "1",
                    "started_at": "2026-09-13T00:00:00Z",
                    "log_path": "run.jsonl",
                    "session_id": "session-1",
                },
                "sandbox": "off",
            }
        )
    )
    outside = tmp_path / "outside-ledger"
    outside.write_text(
        json.dumps(
            {
                "launch_id": "launch-1",
                "activation_id": "activation-1",
                "pid": 1,
                "at": "2026-09-13T00:00:00Z",
            }
        )
        + "\n"
    )
    (activation_dir / "exec.ledger").symlink_to(outside)

    collected = _collect(
        FakeReadClient(_task_rows()),
        "stage-1",
        runtime_roots={"root-1": runtime_root},
    )

    assert not [item for item in collected.observations if item.event_id == "turn-1"]
    assert "exec-ledger-invalid" in {item.code for item in collected.diagnostics}


def test_module_cli_is_the_supported_entrypoint() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "workflow_interpreter.costs", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--config" in completed.stdout
    assert "task" in completed.stdout
    assert "cohort" in completed.stdout


def test_actual_cli_reads_local_fake_bd_and_emits_json(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(_task_rows()))
    fake_bd = tmp_path / "fake-bd"
    fake_bd.write_text(
        "#!" + sys.executable + "\n"
        "import json, sys\n"
        f"rows = json.load(open({str(rows_path)!r}, encoding='utf-8'))\n"
        "command = sys.argv[5]\n"
        "args = sys.argv[6:]\n"
        "if command == 'show':\n"
        "    selected = [r for r in rows if r['id'] == args[0]]\n"
        "elif command == 'list':\n"
        "    filters = [args[i + 1] for i, value in enumerate(args) "
        "if value == '--metadata-field']\n"
        "    selected = rows\n"
        "    for item in filters:\n"
        "        key, value = item.split('=', 1)\n"
        "        selected = [r for r in selected "
        "if str(r.get('metadata', {}).get(key)) == value]\n"
        "else:\n"
        "    raise SystemExit(9)\n"
        "sys.stdout.write(json.dumps(selected))\n"
    )
    fake_bd.chmod(0o755)
    repo = tmp_path / "repo"
    # A git entry and a ledger, because `costs` now opens the ledger `mode=ro`
    # and REFUSES when there is none: a report that silently omitted every
    # ledger-backed root would read like a task that cost nothing (§3.4).
    (repo / ".git").mkdir(parents=True)
    wrapper_home = tmp_path / "wrapper"
    wrapper_root = (
        wrapper_home / hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:16]
    )
    config = tmp_path / "foreman.toml"
    config.write_text(
        f'repo_root = "{repo}"\n'
        f'wrapper_home = "{wrapper_home}"\n'
        'host = "fixture"\n'
        'actor = "fixture"\n'
        "[bd]\n"
        f'workspace = "{repo}"\n'
        'actor = "fixture"\n'
        f'binary = "{fake_bd}"\n'
        "[inspector]\n"
        f'repo_root = "{repo}"\n'
        f'wrapper_root = "{wrapper_root}"\n'
        'host = "fixture"\n'
    )
    # The record is a ledger row since S4 (§3.2, R4) and the CLI reads it from
    # there, so the stage has to HAVE one: without it the report is about a
    # task whose execution identity is unavailable, not about this one.
    database = open_ledger(repo, wrapper_root)
    seeded_records(
        ContractorRecord.model_validate(_record()),
        brief=None,
        into=LedgerContractorRecords(database, backend=BackendKind.BD),
    )
    database.close()
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "workflow_interpreter.costs",
            "--config",
            str(config),
            "--prices",
            str(project_root / "config/task-cost-prices-2026-09-13.json"),
            "task",
            "stage-1",
            "--format",
            "json",
            "--normalize-standard",
            "--supplement",
            str(project_root / "tests/fixtures/task_cost/supplement.json"),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["task_id"] == "stage-1"
    assert report["cost_basis"] == "whole-task"
    assert report["pricing_basis"] == "standard-rate-normalization"

    text_command = [item for item in completed.args if item not in ("--format", "json")]
    text_completed = subprocess.run(
        text_command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert text_completed.returncode == 0, text_completed.stderr
    assert (
        "cost interpretation: API-equivalent estimate; not actual billing"
        in text_completed.stdout
    )
    assert "pricing basis: standard-rate-normalization" in text_completed.stdout
    assert "price snapshot: latest-available (2026-09-13)" in text_completed.stdout


PRICES: Final[Path] = (
    Path(__file__).resolve().parents[1] / "config/task-cost-prices-2026-09-13.json"
)
"""The shipped price book, so a CLI refusal test fails for its own reason."""


def _costs_config(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A foreman config over a fresh repository that has no ledger yet."""
    from tests._ledger import config_file

    return config_file(tmp_path)


def test_costs_against_a_missing_ledger_creates_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """§3.4: a read-only command never writes, and never migrates.

    `open_ledger` would have CREATED and migrated the database — writes, from
    the one command the plan calls read-only — and the `is_file()` check that
    guarded it could be invalidated between the answer and the open.
    """
    from workflow_interpreter.costs.__main__ import main
    from workflow_interpreter.ledger.paths import ledger_path

    config, repo_root, _ = _costs_config(tmp_path)

    code = main(["--config", str(config), "--prices", str(PRICES), "task", "cr-3411.4"])

    assert code == 2
    assert "no ledger to read" in capsys.readouterr().err
    assert not ledger_path(repo_root).exists()


def test_costs_against_an_older_schema_refuses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A schema this build does not know means columns that mean something else."""
    from workflow_interpreter.costs.__main__ import main
    from workflow_interpreter.ledger.database import connect
    from workflow_interpreter.ledger.paths import ledger_path
    from workflow_interpreter.ledger.schema import SCHEMA_VERSION

    config, repo_root, _ = _costs_config(tmp_path)
    path = ledger_path(repo_root)
    behind = connect(path)
    behind.execute("CREATE TABLE ancient (id TEXT PRIMARY KEY)")
    behind.close()
    before = path.read_bytes()

    code = main(["--config", str(config), "--prices", str(PRICES), "task", "cr-3411.4"])

    assert code == 2
    message = capsys.readouterr().err
    assert "never migrates" in message
    assert str(SCHEMA_VERSION) in message
    assert path.read_bytes() == before
