"""`parse_output` against real captured streams, and the tolerance it must have.

Every assertion here runs over bytes a real CLI really produced (see
`tests/_profiles.py` for provenance). The tolerance cases are not hypothetical:
`launch.py::_child` dup2s the runner log onto BOTH fd 1 and fd 2, so a profile's
"machine event stream" is guaranteed to contain the vendor's stderr chatter —
every CLI probed writes a stdin complaint there — and a crash is guaranteed to
be able to leave a half-written final line (drill 18).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final

import pytest
from structlog.testing import capture_logs

from tests._profiles import (
    FORBIDDEN,
    fixture_files,
    make_claude,
    make_codex,
    make_opencode,
    read_stream,
    redact,
)
from tests._supervisor import FrozenClock, handle_for
from workflow_interpreter.profiles import fold_usage
from workflow_interpreter.profiles._base import BaseProfile
from workflow_interpreter.supervisor.profile import EventType

SESSION_MISMATCH: Final[str] = "wf.profile.session_mismatch"
"""The m13 warning event, named once so the test and `_base` cannot drift."""

TORN: Final[list[str]] = [
    '{"type":"system","subtype":"init","session_id":"s-1"}',
    "Reading additional input from stdin...",
    "",
    "   ",
    "2026-08-26T10:06:19Z ERROR codex_core::tools::router: error=patch rejected",
    "42",
    '["not", "an", "object"]',
    '{"type":"result","subtype":"suc',
]
"""One line of each way a runner log can disappoint a parser: a real event, a
stderr sentence, blank lines, a tracing line, valid-but-not-an-object JSON, and
the torn tail a kill leaves behind."""


def profiles(tmp_path: Path) -> list[BaseProfile]:
    """One of each vendor, sharing a frozen clock."""
    clock = FrozenClock()
    return [
        make_claude(tmp_path, clock),
        make_codex(tmp_path, clock),
        make_opencode(tmp_path, clock),
    ]


# --- real streams ---------------------------------------------------------


def test_claude_stream_normalizes_to_messages_tools_and_one_result(
    tmp_path: Path,
) -> None:
    """The `ro` probe's stream: a read, an allowed write and a denied one."""
    profile = make_claude(tmp_path, FrozenClock())

    events = list(profile.parse_output(read_stream("claude", "tools.jsonl")))

    assert [event.type for event in events].count(EventType.RESULT) == 1
    assert [event.type for event in events].count(EventType.TOOL) == 6
    assert not [event for event in events if event.is_error]
    terminal = events[-1]
    assert terminal.type is EventType.RESULT
    assert terminal.session == "2a3dfa4d-f968-450f-8729-649017e808b6"


def test_claude_usage_is_the_terminal_total_not_the_sum_of_the_messages(
    tmp_path: Path,
) -> None:
    """Probed: `assistant` repeats one message's usage once per content block.

    Six `assistant` lines carry two distinct messages, so summing them yields
    in=12/out=24 against a real in=6/out=643. Taking the cumulative `result`
    total is the only arithmetic that matches what was spent.
    """
    profile = make_claude(tmp_path, FrozenClock())

    usage = fold_usage(profile.parse_output(read_stream("claude", "tools.jsonl")))

    assert usage.known is True
    assert usage.input_tokens == 6
    assert usage.output_tokens == 643


def test_money_keeps_the_vendors_own_decimal_repr(tmp_path: Path) -> None:
    """`bdio.Usage` stores cost as a STRING because JSON floats are not exact."""
    profile = make_claude(tmp_path, FrozenClock())

    usage = fold_usage(profile.parse_output(read_stream("claude", "oneshot.jsonl")))

    assert usage.cost_usd == "0.012356000000000002"


def test_claude_resume_reports_the_same_session_id_as_the_launch(
    tmp_path: Path,
) -> None:
    """Drill 14's "session id identical" half, over the real captured pair.

    claude is the vendor §5.2 can pre-assign for, so the pair also proves the
    wrapper-minted UUID survives: both streams carry the id the launch was
    given, and `--resume` neither renames nor forks it.
    """
    profile = make_claude(tmp_path, FrozenClock())

    launch = list(profile.parse_output(read_stream("claude", "oneshot.jsonl")))
    resumed = list(profile.parse_output(read_stream("claude", "resume.jsonl")))

    assert {event.session for event in launch if event.session} == {
        "f50464f9-759c-4540-99bd-61657682151b"
    }
    assert {event.session for event in resumed if event.session} == {
        "f50464f9-759c-4540-99bd-61657682151b"
    }


def test_codex_session_comes_from_the_first_thread_started_line(
    tmp_path: Path,
) -> None:
    """Codex has no way to pre-assign an id; this line is where it exists (§5.2)."""
    profile = make_codex(tmp_path, FrozenClock())

    events = list(profile.parse_output(read_stream("codex", "oneshot.jsonl")))

    assert events[0].session == "01a03d87-cda2-7062-aa5d-b5a73dc882c3"
    assert all(event.session is None for event in events[1:])


def test_codex_resume_reports_the_same_thread_id_as_the_launch(
    tmp_path: Path,
) -> None:
    """Drill 14's "session id identical" half, over the real captured pair."""
    profile = make_codex(tmp_path, FrozenClock())

    launch = list(profile.parse_output(read_stream("codex", "oneshot.jsonl")))
    resumed = list(profile.parse_output(read_stream("codex", "resume.jsonl")))

    assert launch[0].session == resumed[0].session


def test_codex_reports_tokens_and_no_cost(tmp_path: Path) -> None:
    """`codex exec --json` carries no money field at all (probed)."""
    profile = make_codex(tmp_path, FrozenClock())

    usage = fold_usage(profile.parse_output(read_stream("codex", "commands.jsonl")))

    assert (usage.input_tokens, usage.output_tokens) == (104208, 564)
    assert usage.cost_usd is None


def test_codex_shell_steps_normalize_to_tool_events(tmp_path: Path) -> None:
    """`item.*` lines whose item is a `command_execution` are the tool steps."""
    profile = make_codex(tmp_path, FrozenClock())

    events = list(profile.parse_output(read_stream("codex", "commands.jsonl")))

    tools = [event for event in events if event.type is EventType.TOOL]
    assert len(tools) == 6
    assert any("curl" in event.text for event in tools)


def test_a_failing_codex_run_yields_error_events_and_unknown_usage(
    tmp_path: Path,
) -> None:
    """§6: `usage: unknown` is legal telemetry.

    The stream is a real 401 run — the shape a broken or unauthenticated CLI
    produces, which drill 22 has to classify as transport rather than verdict.
    """
    profile = make_codex(tmp_path, FrozenClock())

    events = list(profile.parse_output(read_stream("codex", "auth_error.jsonl")))

    assert [event for event in events if event.is_error]
    assert all(event.type is EventType.ERROR for event in events if event.is_error)
    assert fold_usage(events).known is False


def test_opencode_reports_usage_per_step_and_a_result_only_at_the_stop(
    tmp_path: Path,
) -> None:
    """Per-step counts are not cumulative (probed), so they are summed."""
    profile = make_opencode(tmp_path, FrozenClock())

    events = list(profile.parse_output(read_stream("opencode", "tools.jsonl")))

    kinds = [event.type for event in events]
    assert kinds.count(EventType.USAGE) == 1
    assert kinds.count(EventType.RESULT) == 1
    assert kinds.count(EventType.TOOL) == 1
    usage = fold_usage(events)
    assert (usage.input_tokens, usage.output_tokens) == (7268, 44)


def test_opencode_carries_the_session_on_every_line(tmp_path: Path) -> None:
    """Unlike codex, opencode repeats `sessionID` on each event."""
    profile = make_opencode(tmp_path, FrozenClock())

    events = list(profile.parse_output(read_stream("opencode", "oneshot.jsonl")))

    assert {event.session for event in events} == {"ses_fc2738efcffeTn5yyfIpiSYcqS"}


def _denials(vendor: str, name: str) -> list[dict[str, object]]:
    """The `permission_denials` the captured run recorded, straight from the file.

    Read raw rather than through `parse_output` on purpose: the profile has no
    reason to normalize a denial into a §6 event, and the claim being checked is
    about the CAPTURE — that these fixtures are a real bounded run, and that the
    bound the argv asks for is the bound the CLI applied.
    """
    for line in read_stream(vendor, name):
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("type") == "result" or "permission_denials" in payload:
            denials = payload.get("permission_denials")
            if isinstance(denials, list):
                return [item for item in denials if isinstance(item, dict)]
    raise AssertionError(f"{vendor}/{name} carries no result line")


def test_the_captured_writing_run_shows_the_cli_enforcing_the_profiles_bound(
    tmp_path: Path,
) -> None:
    """m11: `writes.jsonl` is the `writes = true` probe, and it is evidence.

    Two writes inside the bound landed, and exactly two things were refused —
    the write outside both the checkout and the wrapper directory, and
    `git push`. That is the danger-default matrix, recorded by the CLI itself
    rather than asserted about an argv, and the fixture went unreferenced.
    """
    profile = make_claude(tmp_path, FrozenClock())
    events = list(profile.parse_output(read_stream("claude", "writes.jsonl")))

    denied = _denials("claude", "writes.jsonl")

    assert [item["tool_name"] for item in denied] == ["Write", "Bash"]
    refused = [str(item.get("tool_input")) for item in denied]
    assert any("outside.txt" in item for item in refused)
    assert any("git push" in item for item in refused)
    # The in-bounds writes are in the same stream and were NOT refused.
    tools = [event.text for event in events if event.type is EventType.TOOL]
    assert any("Write" in text for text in tools)
    assert not any("rw-tree/tree.txt" in item for item in refused)
    assert not any("rw-wf/artifacts" in item for item in refused)


def test_a_run_that_stayed_inside_its_bound_records_no_denials(
    tmp_path: Path,
) -> None:
    """m11: `result.json` — the `--output-format json` capture, also unreferenced.

    A single JSON object rather than a stream, which the profile parses as one
    terminal event; its empty `permission_denials` is what "the bound was never
    reached" looks like, so an assertion about denials has a control.
    """
    profile = make_claude(tmp_path, FrozenClock())

    events = list(profile.parse_output(read_stream("claude", "result.json")))

    assert _denials("claude", "result.json") == []
    assert [event.type for event in events] == [EventType.RESULT]
    assert events[0].is_error is False
    assert events[0].session == "266ea188-88b8-4707-ad99-4c99b85f2268"


# --- tolerance ------------------------------------------------------------


def test_no_parser_raises_on_a_torn_or_foreign_line(tmp_path: Path) -> None:
    """The contract: never raise. A crash-loop is worse than an unread line."""
    for profile in profiles(tmp_path):
        events = list(profile.parse_output(TORN))

        assert [event for event in events if event.is_error]
        assert all(event.type is EventType.ERROR for event in events if event.is_error)


def test_blank_lines_are_dropped_and_everything_else_is_kept(tmp_path: Path) -> None:
    """A blank line carries nothing; a garbage line carries evidence."""
    for profile in profiles(tmp_path):
        events = list(profile.parse_output(TORN))

        assert len(events) == len([line for line in TORN if line.strip()])
        assert any(
            "Reading additional input" in event.text
            for event in events
            if event.is_error
        )


def test_a_foreign_vendors_stream_parses_without_raising(tmp_path: Path) -> None:
    """The log is shared with stderr; nothing guarantees the lines are ours."""
    claude = make_claude(tmp_path, FrozenClock())

    events = list(claude.parse_output(read_stream("codex", "commands.jsonl")))

    assert events
    assert fold_usage(events).known is False


def test_a_well_formed_line_the_decoder_refuses_is_an_error_not_a_crash(
    tmp_path: Path,
) -> None:
    """M7: the JSON parse was guarded and the DECODER was not.

    A token count outside `bdio`'s carrier bounds is exactly the shape bd's JSON
    path would silently round, so `Usage` refuses it — and the refusal used to
    propagate out of `parse_output`. `collect_terminal_envelope` re-reads the
    log after every exit, so one such line would have crashed the wrapper on
    every subsequent tick rather than once.
    """
    profile = make_codex(tmp_path, FrozenClock())
    huge = 10**30
    completed = (
        f'{{"type":"turn.completed","usage":{{"input_tokens":{huge},'
        f'"output_tokens":1}}}}'
    )
    stream = ['{"type":"thread.started","thread_id":"t-1"}', completed]

    events = list(profile.parse_output(stream))

    assert [event.type for event in events] == [EventType.MESSAGE, EventType.ERROR]
    assert events[1].is_error is True
    assert "ValidationError" in events[1].text
    assert str(huge) in events[1].text
    assert fold_usage(events).known is False


def test_a_stream_with_no_usage_at_all_is_unknown_not_zero(tmp_path: Path) -> None:
    """§6 again: absent usage is a legal state, and it is not the number zero."""
    profile = make_claude(tmp_path, FrozenClock())

    usage = fold_usage(profile.parse_output(['{"type":"system","subtype":"init"}']))

    assert usage.known is False
    assert usage.input_tokens is None


# --- fixture provenance ---------------------------------------------------


def test_every_committed_fixture_is_a_fixed_point_of_the_declared_redactor() -> None:
    """m16: the provenance claim is executable, and therefore checkable.

    "Two host substitutions and nothing else" was the claim; one capture had its
    IPC socket pid normalized and three did not, so the claim was false and
    nobody could have told. Running the declared redaction over a committed
    fixture must now change nothing — which is only true if every capture went
    through the same list.
    """
    files = [path for path in fixture_files() if path.suffix != ".md"]
    assert files, "no captured streams to check"
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert redact(text) == text, path.name


def test_no_committed_fixture_carries_a_host_or_credential_string() -> None:
    """The negative half of provenance, as patterns rather than as a memory."""
    for path in fixture_files():
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            assert not re.search(pattern, text), (path.name, pattern)


# --- the terminal envelope ------------------------------------------------


def write_log(tmp_path: Path, vendor: str, name: str) -> Path:
    """Lay a captured stream down where a handle's `log_path` would point."""
    activation_dir = tmp_path / ".wf" / "root" / "wf-42"
    activation_dir.mkdir(parents=True, exist_ok=True)
    log = activation_dir / "run.jsonl"
    log.write_text(
        (Path(__file__).parent / "fixtures" / "profiles" / vendor / name).read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    return log


def test_the_envelope_reports_usage_session_and_duration(tmp_path: Path) -> None:
    """§6's `collect_terminal_envelope(handle) -> {usage, session, duration}`."""
    clock = FrozenClock()
    log = write_log(tmp_path, "codex", "commands.jsonl")
    profile = make_codex(tmp_path, clock)
    clock.advance(90.0)

    envelope = profile.collect_terminal_envelope(handle_for(1, log_path=str(log)))

    assert envelope.session_id == "01a03d91-f8e8-7310-85f1-6ca11d1d45a1"
    assert envelope.usage.input_tokens == 104208
    assert envelope.duration_s == pytest.approx(90.0)


def test_the_envelope_reports_no_marker_because_the_claim_is_not_a_profiles(
    tmp_path: Path,
) -> None:
    """m14: §7.2's claim is `exit.py`'s, read from the reserved channel itself.

    A profile-reported marker was never consumed and could only be produced by
    guessing `$WF_OUTCOME_FILE`'s path from `handle.log_path`. A marker sitting
    beside the log is deliberately present here, and the envelope has nowhere to
    put it.
    """
    log = write_log(tmp_path, "codex", "commands.jsonl")
    (log.parent / "outcome.json").write_text('{"outcome":"done"}', encoding="utf-8")
    profile = make_codex(tmp_path, FrozenClock())

    envelope = profile.collect_terminal_envelope(handle_for(1, log_path=str(log)))

    assert not hasattr(envelope, "marker")
    assert set(envelope.model_dump()) == {"usage", "session_id", "duration_s"}


def test_the_envelope_survives_a_missing_log(tmp_path: Path) -> None:
    """A dead-before-writing runner still has to produce a gradeable envelope."""
    profile = make_claude(tmp_path, FrozenClock())

    envelope = profile.collect_terminal_envelope(
        handle_for(1, log_path=str(tmp_path / "nowhere" / "run.jsonl"))
    )

    assert envelope.usage.known is False
    assert envelope.session_id == "sess-super-1"


def test_a_session_the_stream_disagrees_with_is_reported_and_logged(
    tmp_path: Path,
) -> None:
    """m13: `scan.session or handle.session_id` never compared the two.

    claude's id is pre-assigned and echoed back (§5.2), so a difference means
    the CLI ignored `--session-id` and the recorded handle names a session that
    cannot be resumed. The observed one wins because it is the session that
    exists; the disagreement is warned about rather than swallowed.

    The WARNING is asserted, not just the return value. m13's whole behavioural
    delta is the log line — the return is unchanged by design — so a test that
    checked only the return would stay green if somebody simplified
    `_session_of` back to `observed or assigned`, which is exactly the code m13
    replaced.
    """
    log = write_log(tmp_path, "claude", "oneshot.jsonl")
    profile = make_claude(tmp_path, FrozenClock())

    with capture_logs() as captured:
        envelope = profile.collect_terminal_envelope(handle_for(1, log_path=str(log)))

    assert handle_for(1).session_id == "sess-super-1"
    assert envelope.session_id == "f50464f9-759c-4540-99bd-61657682151b"
    assert [entry for entry in captured if entry["event"] == SESSION_MISMATCH] == [
        {
            "event": SESSION_MISMATCH,
            "log_level": "warning",
            "runner": "claude",
            "assigned": "sess-super-1",
            "observed": "f50464f9-759c-4540-99bd-61657682151b",
        }
    ]


def test_a_session_the_stream_agrees_with_is_not_warned_about(tmp_path: Path) -> None:
    """The control: a warning on every envelope would carry no information.

    Same profile, same log, and the handle carrying the id the stream names —
    which is the ordinary case, and must be silent for the assertion above to
    mean anything.
    """
    log = write_log(tmp_path, "claude", "oneshot.jsonl")
    profile = make_claude(tmp_path, FrozenClock())
    agreed = handle_for(1, log_path=str(log)).model_copy(
        update={"session_id": "f50464f9-759c-4540-99bd-61657682151b"}
    )

    with capture_logs() as captured:
        envelope = profile.collect_terminal_envelope(agreed)

    assert envelope.session_id == "f50464f9-759c-4540-99bd-61657682151b"
    assert [entry for entry in captured if entry["event"] == SESSION_MISMATCH] == []


def test_the_envelope_prefers_the_session_the_stream_names(tmp_path: Path) -> None:
    """For codex and opencode the handle's id is empty until the stream names one."""
    log = write_log(tmp_path, "opencode", "oneshot.jsonl")
    profile = make_opencode(tmp_path, FrozenClock())

    envelope = profile.collect_terminal_envelope(handle_for(1, log_path=str(log)))

    assert envelope.session_id == "ses_fc2738efcffeTn5yyfIpiSYcqS"
