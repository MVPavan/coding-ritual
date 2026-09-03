"""Unit tests for the bd transport: argv construction and read-back verification.

No bd process runs here — a recording `CommandRunner` stands in, so the
assertions are about what the client would spawn and how it reacts to what bd
returns.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest

from workflow_interpreter.bdio.client import (
    ALLOWED_FLAGS,
    BdClient,
    BdSubcommand,
    CompletedCommand,
)
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.errors import (
    BdCommandError,
    BdConfigError,
    BdOutputError,
    ForbiddenInvocationError,
    LossyWriteError,
)
from workflow_interpreter.bdio.wire import IssueType, Metadata

WORKSPACE: Final[Path] = Path("/tmp/wf-lab")
ACTOR: Final[str] = "wf-test"
BEAD_ID: Final[str] = "wf-1"


class RecordingRunner:
    """A `CommandRunner` that records argvs and replays scripted stdout."""

    def __init__(self, responses: Sequence[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[tuple[str, ...], float]] = []
        self.metadata_bodies: list[str] = []

    def __call__(self, argv: Sequence[str], timeout_s: float) -> CompletedCommand:
        self.calls.append((tuple(argv), timeout_s))
        # Metadata travels as `@<path>` (ADR 0003) and the transport deletes
        # the file as soon as the call returns, so a faithful stand-in must
        # read it here — exactly when real bd would.
        if "--metadata" in argv:
            value = argv[argv.index("--metadata") + 1]
            if value.startswith("@"):
                self.metadata_bodies.append(Path(value[1:]).read_text(encoding="utf-8"))
        stdout = self.responses.pop(0) if self.responses else ""
        return CompletedCommand(returncode=0, stdout=stdout, stderr="")


def _row(metadata: Metadata, **overrides: object) -> str:
    """A `bd show --json` response carrying `metadata`."""
    row = {
        "id": BEAD_ID,
        "title": "t",
        "status": "open",
        "issue_type": "task",
        "metadata": metadata,
    } | overrides
    return json.dumps([row])


def _client(responses: Sequence[str]) -> tuple[BdClient, RecordingRunner]:
    """A client wired to a scripted runner."""
    runner = RecordingRunner(responses)
    config = BdConfig(workspace=WORKSPACE, actor=ACTOR, command_timeout_s=12.5)
    return BdClient(config, runner), runner


# --- argv construction ---------------------------------------------------


def test_every_invocation_is_an_argv_list_with_globals_first() -> None:
    client, runner = _client([json.dumps({"backend": "dolt"})])
    client.context()
    argv, timeout_s = runner.calls[0]
    assert argv[:6] == (
        "bd",
        "-C",
        str(WORKSPACE),
        "--actor",
        ACTOR,
        BdSubcommand.CONTEXT.value,
    )
    assert timeout_s == 12.5


def test_every_call_carries_the_configured_timeout() -> None:
    client, runner = _client([BEAD_ID, _row({"k": "v"})])
    client._create_bead(title="t", metadata={"k": "v"})
    assert [timeout for _, timeout in runner.calls] == [12.5, 12.5]


def test_no_argv_token_is_a_shell_string() -> None:
    client, runner = _client([BEAD_ID, _row({"k": "v; rm -rf /"})])
    client._create_bead(title="a; rm -rf /", metadata={"k": "v; rm -rf /"})
    argv, _ = runner.calls[0]
    # The hostile title travels as its own argv element; nothing splits it.
    assert "a; rm -rf /" in argv
    # The metadata VALUE reaches argv not at all: it travels as `@<path>`
    # since ADR 0003, so a hostile value is never a command-line token. What
    # argv carries is the path, and the file holds the exact canonical JSON.
    assert argv[argv.index("--metadata") + 1].startswith("@")
    assert not any(token.startswith("{") for token in argv)
    assert runner.metadata_bodies == [
        json.dumps({"k": "v; rm -rf /"}, separators=(",", ":"))
    ]


def test_list_reads_are_always_unlimited_and_include_closed_and_gates() -> None:
    client, runner = _client(["[]"])
    client.list_beads(
        metadata_filters={"wf_root_id": "wf-r"}, issue_type=IssueType.EVENT
    )
    argv, _ = runner.calls[0]
    assert "--limit" in argv
    assert argv[argv.index("--limit") + 1] == "0"
    assert "--all" in argv
    assert "--include-gates" in argv
    assert "--metadata-field" in argv
    assert "wf_root_id=wf-r" in argv


def test_event_payload_is_inline_json_never_an_at_file_reference() -> None:
    payload = {"from": "a", "to": "b"}
    client, runner = _client([BEAD_ID, _row({}, payload=json.dumps(payload))])
    client._create_bead(
        title="e", metadata={}, issue_type=IssueType.EVENT, event_payload=payload
    )
    argv, _ = runner.calls[0]
    value = argv[argv.index("--event-payload") + 1]
    assert value == '{"from":"a","to":"b"}'
    assert not value.startswith("@")


def test_the_flag_allow_list_excludes_every_forbidden_surface() -> None:
    forbidden = {
        "--force",
        "--ignore-schema-skew",
        "--continue",
        "--claim-next",
        "--set-metadata",
        "--readonly",
        "--global",
    }
    assert forbidden.isdisjoint(ALLOWED_FLAGS)


def test_the_subcommand_set_excludes_delete_edit_gate_and_audit() -> None:
    closed_set = {subcommand.value for subcommand in BdSubcommand}
    assert closed_set.isdisjoint({"delete", "edit", "gate", "audit", "bond", "reopen"})


def test_an_unlisted_flag_is_refused_before_the_process_is_spawned() -> None:
    client, runner = _client([])
    with pytest.raises(ForbiddenInvocationError, match="--force"):
        # The only way to smuggle a flag in is through injected config.
        client._run(("bd", "-C", str(WORKSPACE), "--actor", "a", "list", "--force"))
    assert runner.calls == []


def test_an_actor_that_spells_a_flag_is_refused_not_passed_through() -> None:
    client, runner = _client([])
    hostile = BdClient(BdConfig(workspace=WORKSPACE, actor="--force"), runner)
    with pytest.raises(ForbiddenInvocationError):
        hostile.show(BEAD_ID)
    assert runner.calls == []
    assert client.workspace == WORKSPACE


def test_a_relative_workspace_is_refused_at_construction() -> None:
    with pytest.raises(BdConfigError):
        BdClient(BdConfig(workspace=Path("relative/lab"), actor=ACTOR))


# --- read-back verification ---------------------------------------------


def test_a_dropped_metadata_key_raises() -> None:
    client, _ = _client([BEAD_ID, _row({"kept": 1})])
    with pytest.raises(LossyWriteError, match="absent after write"):
        client._create_bead(title="t", metadata={"kept": 1, "dropped": 2})


def test_a_mangled_metadata_value_raises() -> None:
    # bd's JSON path rounds integers past float64 precision (probed).
    written = 12345678901234567890
    client, _ = _client([BEAD_ID, _row({"big": 12345678901234567000})])
    with pytest.raises(LossyWriteError, match="read back as"):
        client._create_bead(title="t", metadata={"big": written})


def test_a_stringified_structured_value_raises() -> None:
    # The `--set-metadata` failure mode, caught generically.
    client, _ = _client([BEAD_ID, _row({"obj": '{"x": 1}'})])
    with pytest.raises(LossyWriteError):
        client._create_bead(title="t", metadata={"obj": {"x": 1}})


def test_an_event_payload_stored_as_a_literal_string_raises() -> None:
    # The probed `@file` trap: bd stores "@evt.json" and exits 0.
    client, _ = _client([BEAD_ID, _row({}, payload="@evt.json")])
    with pytest.raises(LossyWriteError, match="unparseable"):
        client._create_bead(
            title="e",
            metadata={},
            issue_type=IssueType.EVENT,
            event_payload={"from": "a"},
        )


def test_a_missing_event_payload_raises() -> None:
    client, _ = _client([BEAD_ID, _row({})])
    with pytest.raises(LossyWriteError, match="absent after write"):
        client._create_bead(
            title="e",
            metadata={},
            issue_type=IssueType.EVENT,
            event_payload={"from": "a"},
        )


def test_a_close_that_did_not_close_raises() -> None:
    client, _ = _client(["", _row({}, status="open")])
    with pytest.raises(LossyWriteError, match="status is"):
        client._close_bead(BEAD_ID, "outcome=done")


def test_a_rewritten_close_reason_raises() -> None:
    client, _ = _client(["", _row({}, status="closed", close_reason="something else")])
    with pytest.raises(LossyWriteError, match="close reason"):
        client._close_bead(BEAD_ID, "outcome=done")


def test_a_successful_write_returns_the_verified_row() -> None:
    client, _ = _client([BEAD_ID, _row({"wf_kind": "activation"})])
    record = client._create_bead(title="t", metadata={"wf_kind": "activation"})
    assert record.id == BEAD_ID
    assert record.metadata["wf_kind"] == "activation"


# --- failure mapping -----------------------------------------------------


class FailingRunner:
    """A runner that always reports a non-zero exit."""

    def __call__(self, argv: Sequence[str], timeout_s: float) -> CompletedCommand:
        return CompletedCommand(returncode=2, stdout="", stderr="boom")


def test_a_non_zero_exit_becomes_a_typed_error() -> None:
    client = BdClient(BdConfig(workspace=WORKSPACE, actor=ACTOR), FailingRunner())
    with pytest.raises(BdCommandError) as caught:
        client.show(BEAD_ID)
    assert caught.value.returncode == 2
    assert caught.value.subcommand == BdSubcommand.SHOW.value


def test_unparseable_json_becomes_a_typed_error() -> None:
    client, _ = _client(["not json"])
    with pytest.raises(BdOutputError, match="did not emit JSON"):
        client.list_beads()


def test_a_show_with_no_row_becomes_a_typed_error() -> None:
    client, _ = _client(["[]"])
    with pytest.raises(BdOutputError, match="returned no row"):
        client.show(BEAD_ID)
