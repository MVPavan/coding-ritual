"""Per-activation usage is a delta, never a sum of cumulative notifications."""

from hashlib import sha256

import pytest

from tests._appserver import AppServerLab
from tests._supervisor import entry_mint
from workflow_interpreter.bdio import MintReason
from workflow_interpreter.contracts.rpc_usage import TokenCounts, UsageSnapshot
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.models import SteerIntent
from workflow_interpreter.supervisor.paths import write_record
from workflow_interpreter.supervisor.rpc_usage import updated_usage


def payload(total, last=10):
    """A pinned-schema usage notification with a deliberately unrelated last call."""
    return {
        "threadId": "thread-1",
        "turnId": "turn-1",
        "tokenUsage": {
            "total": {
                "inputTokens": total,
                "cachedInputTokens": 20,
                "outputTokens": 5,
                "totalTokens": total + 5,
                "reasoningOutputTokens": 2,
            },
            "last": {
                "inputTokens": last,
                "cachedInputTokens": 0,
                "outputTokens": 1,
                "totalTokens": last + 1,
                "reasoningOutputTokens": 0,
            },
        },
    }


def test_cumulative_notifications_are_not_summed_and_cache_is_separate():
    """Duplicate notifications cost nothing; the prior thread baseline is subtracted."""
    baseline = TokenCounts(input=40, cached_input=10, output=2)
    first = updated_usage(payload(100), baseline, envelope_bytes=123)
    again = updated_usage(payload(100), baseline, envelope_bytes=123)
    assert first == again
    assert again.per_turn.input == 60
    assert again.per_turn.cached_input == 10
    assert again.per_turn.output == 3
    assert again.cumulative.input == 100
    assert again.cumulative.unknown["reasoningOutputTokens"] == 2
    assert again.envelope_bytes == 123


def test_unknown_baseline_does_not_manufacture_a_delta():
    """A resumed thread without accounting evidence remains explicitly unknown."""
    usage = updated_usage(payload(100), TokenCounts(), envelope_bytes=1)
    assert usage.per_turn.input is None
    assert usage.cumulative.input == 100


@pytest.mark.parametrize("bad", [-1, True, "10"])
def test_invalid_token_counts_are_refused(bad):
    """Malformed telemetry cannot silently become a budget or billing fact."""
    notification = payload(100)
    notification["tokenUsage"]["total"]["inputTokens"] = bad
    with pytest.raises(ValueError):
        updated_usage(
            notification,
            TokenCounts(input=0, cached_input=0, output=0),
            envelope_bytes=1,
        )


def test_usage_after_completion_is_drained_before_the_reuse_baseline_is_published(
    tmp_path,
):
    """Late cumulative telemetry must not make the next activation overcount."""

    lab = AppServerLab(tmp_path, "late-usage")
    result = lab.run()
    record = lab.store.reads.load_activation(result.dispatch.activation.activation_id)
    assert record.metadata.session_completion.usage.cumulative.input == 150
    assert result.observation.usage.input_tokens == 130


def test_missing_cached_count_preserves_known_input(tmp_path):
    """Missing cache detail cannot erase the known total input count."""

    lab = AppServerLab(tmp_path)
    result = lab.run()
    aid = result.dispatch.activation.activation_id
    write_record(
        lab.paths.activation_dir(aid) / "rpc-usage.json",
        UsageSnapshot(per_turn=TokenCounts(input=17, output=3)),
    )
    usage = lab.profile.collect_terminal_envelope(result.dispatch.handle).usage
    assert usage.known
    assert usage.input_tokens == 17
    assert usage.cache_read_input_tokens is None


def test_steer_continuation_uses_last_protected_usage_without_completed_turn(tmp_path):
    """An interrupted source may have real cumulative usage despite no completion."""

    lab = AppServerLab(tmp_path)
    first = lab.run()
    aid = first.dispatch.activation.activation_id
    lab.store._client._merge_metadata(aid, {"session_completion": None})
    lab.store.close_activation(aid, Outcome.STEERED)

    request = entry_mint(runner_profile="codex-appserver", session_id="").model_copy(
        update={
            "mint_reason": MintReason.STEER_CONTINUATION,
            "predecessor_activation_id": aid,
        }
    )
    instructions = "continue with the current envelope"
    write_record(
        lab.paths.steer_intent(aid),
        SteerIntent(
            activation_id=aid,
            reason="test",
            instructions=instructions,
            instructions_digest=sha256(instructions.encode()).hexdigest(),
            requested_at="test",
            continuation=request,
        ),
    )
    second = lab.run(request)
    assert second.observation.usage.known
    assert second.observation.usage.input_tokens == 80
    assert second.observation.usage.cache_read_input_tokens == 20
