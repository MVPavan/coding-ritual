"""Causal, immutable host diagnostics survive rework and wrapper cleanup."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tests._foreman import register_lab_catalog_session
from tests._helpers import VALID_FIXTURE
from tests.conftest import Signer
from tests.test_foreman_fail_code_routing import (
    RED_IF_MARKER,
    RED_MARKER,
    REVIEW_RED_IF_MARKER,
    REVIEW_RED_MARKER,
    _implement,
    _lab,
    _reviews,
    _writes,
)
from workflow_interpreter.bdio import (
    CarrierIntegrityError,
    Evidence,
    Outcome,
    SigningConfig,
)
from workflow_interpreter.foreman.inputs import InputsUnavailable, materialize
from workflow_interpreter.foreman.verify_feedback import bounded_payload
from workflow_interpreter.inspector.models import CompletionEvidence, VerifyResult
from workflow_interpreter.inspector.sandbox import SandboxMode


def feedback_graph(tmp_path: Path, *, consumer: str = "implement") -> Path:
    """Add feedback only to the selected consumer of a historical graph."""
    text = VALID_FIXTURE.read_text()
    start = text.index('name          = "' + consumer + '"')
    offset = text.index("inputs", start)
    opening = text.index("[", offset)
    text = text[: opening + 1] + '"verify_failure", ' + text[opening + 1 :]
    text += '\n[[source]]\nname="verify_failure"\nproducer="engine:verify_failure"\noptional=true\ntrim_priority=10\n'
    path = tmp_path / "feedback.toml"
    path.write_text(text)
    return path


def test_rework_binds_host_failure_and_survives_completion_removal(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Real tick/mint/composition pins captured diagnostics, never mutable logs."""
    graph = feedback_graph(tmp_path)
    script = RED_IF_MARKER.replace("test !", "echo diagnostic-tail\ntest !")
    lab = _lab(tmp_path, signing_config, sign_payload, toml=graph, verify=script)
    root = lab.instantiate()
    first = _implement(lab, _writes(RED_MARKER))
    assert all(
        b.name != "verify_failure"
        for b in lab.store.reads.load_activation(first).metadata.inputs
    )
    lab.profiles.next_script(_writes("src/feature.py"))
    second = lab.tick().dispatched
    assert second is not None
    activation = lab.store.reads.load_activation(second)
    binding = next(b for b in activation.metadata.inputs if b.name == "verify_failure")
    assert binding.verify_failure.source_activation_id == first
    source = lab.store.reads.load_activation(first)
    wiring = lab.wiring()
    wiring.paths.completion(first).unlink()
    recovered = materialize(lab.git, lab.repo, root, binding, source)
    assert "diagnostic-tail" in recovered.text
    assert "host-observed diagnostic data" in recovered.text
    assert "diagnostic-tail" in lab.profiles.profile.tasks[-1].brief
    assert "verify_failure" in activation.metadata.envelope["included"]
    tampered = binding.model_copy(update={"digest": "0" * 64})
    with pytest.raises(InputsUnavailable):
        materialize(lab.git, lab.repo, root, tampered, source)


def test_cross_node_fail_code_binds_reviewer_host_check(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """The edge supplies causality even when the failing producer is a reviewer."""
    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=feedback_graph(tmp_path),
        review=REVIEW_RED_IF_MARKER,
    )
    lab.instantiate()
    _implement(lab, _writes(REVIEW_RED_MARKER))
    lab.profiles.next_script(_reviews("accept"))
    reviewer = lab.tick().dispatched
    assert lab.tick().settled == reviewer
    rework = lab.tick().dispatched
    bindings = lab.store.reads.load_activation(rework).metadata.inputs
    assert (
        next(b for b in bindings if b.name == "verify_failure").producer_activation_id
        == reviewer
    )


def test_reviewer_consumer_refused_before_root_write(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Even an optional engine diagnostic source is forbidden for reviewers."""
    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=feedback_graph(tmp_path, consumer="review"),
    )
    with pytest.raises(CarrierIntegrityError, match="writer"):
        lab.instantiate()


def test_payload_cap_is_deterministic_and_retains_final_tails() -> None:
    """Aggregate trimming reports omissions and keeps UTF-8 and final attempts."""
    result = VerifyResult(
        cmd="scripts/check",
        exit_code=1,
        script_digest="a" * 64,
        pinned_digest="a" * 64,
        provenance_ok=True,
        attempts=2,
        output_tails=("old" * 600, "終" * 600),
    )
    completion = CompletionEvidence(
        outcome=Outcome.FAIL_CODE,
        claimed_outcome=None,
        evidence=Evidence(),
        verify_results=(result,) * 20,
    )
    body = bounded_payload("root", "source", completion)
    assert body == bounded_payload("root", "source", completion)
    assert len(body) <= 16 * 1024
    payload = json.loads(body)
    assert payload["omitted_checks"] > 0
    assert payload["omitted_bytes"] > 0
    assert payload["checks"][0]["output_tails"][-1] == "終" * 600
    assert "attempt_exit_codes" not in payload["checks"][0]


def test_old_failure_is_not_reused_after_reviewer_rejection(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """A later reject is its own cause, regardless of older failed checks."""
    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=feedback_graph(tmp_path),
        verify=RED_IF_MARKER,
    )
    lab.instantiate()
    _implement(lab, _writes(RED_MARKER))
    lab.profiles.next_script(_writes("src/feature.py"))
    rework = lab.tick().dispatched
    assert lab.tick().settled == rework
    lab.profiles.next_script(_reviews("reject"))
    reviewer = lab.tick().dispatched
    assert lab.tick().settled == reviewer
    next_id = lab.tick().dispatched
    assert next_id is not None
    assert all(
        b.name != "verify_failure"
        for b in lab.store.reads.load_activation(next_id).metadata.inputs
    )


def test_marker_only_fail_code_has_no_host_feedback(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """A claimed fail_code with green host checks supplies no diagnostic source."""
    from tests._inspector import ChildScript

    lab = _lab(tmp_path, signing_config, sign_payload, toml=feedback_graph(tmp_path))
    lab.instantiate()
    _implement(
        lab, ChildScript(marker='{"outcome":"fail_code"}', effects='{"paths":[]}')
    )
    successor = lab.tick().dispatched
    assert successor is not None
    assert all(
        b.name != "verify_failure"
        for b in lab.store.reads.load_activation(successor).metadata.inputs
    )


def test_bound_feedback_reference_exports_verified_blob(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Reference consumers get the same immutable diagnostics in read-only evidence."""
    graph = feedback_graph(tmp_path)
    graph.write_text(
        graph.read_text().replace(
            'name          = "implement"',
            'name          = "implement"\nartifact_input_mode = "references"',
        )
    )
    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=graph,
        verify=RED_IF_MARKER,
        sandbox=SandboxMode.BWRAP,
    )
    lab.instantiate()
    _implement(lab, _writes(RED_MARKER))
    successor = lab.tick().dispatched
    assert successor is not None
    task = lab.profiles.profile.tasks[-1]
    assert "index_path" in task.brief
    exports = list(
        lab.wiring().paths.activation_dir(successor).glob("evidence/*/report-000.txt")
    )
    assert any("host-observed diagnostic data" in p.read_text() for p in exports)
    assert all(
        not p.is_relative_to(Path(task.channels.outcome_file).parent) for p in exports
    )


def test_feedback_follows_verified_exhaustion_rebudget(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """A bound-limited fail_code edge keeps its cause across the signed gate."""
    from workflow_interpreter.bdio import BoundMutation

    graph = feedback_graph(tmp_path)
    graph.write_text(graph.read_text().replace("max_entries  = 3", "max_entries  = 1"))
    lab = _lab(tmp_path, signing_config, sign_payload, toml=graph, verify=RED_IF_MARKER)
    lab.instantiate()
    source = _implement(lab, _writes(RED_MARKER))
    gate = lab.tick().opened_gate
    assert gate is not None
    lab.approve(
        gate,
        Outcome.REBUDGET,
        mutation=BoundMutation(key="region.build-review.max_entries", value=3),
    )
    lab.tick()
    successor = lab.tick().dispatched
    assert successor is not None
    binding = next(
        b
        for b in lab.store.reads.load_activation(successor).metadata.inputs
        if b.name == "verify_failure"
    )
    assert binding.producer_activation_id == source


@pytest.mark.parametrize("continuation", ["retry", "steer"])
def test_retry_and_steer_keep_the_original_blob_without_completion_file(
    tmp_path: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
    continuation: str,
) -> None:
    """A continuation inherits evidence instead of searching for another failure."""
    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=feedback_graph(tmp_path),
        verify=RED_IF_MARKER,
    )
    lab.instantiate()
    source = _implement(lab, _writes(RED_MARKER))
    rework = lab.tick().dispatched
    assert rework is not None
    original = lab.store.reads.load_activation(rework).metadata.inputs
    lab.wiring().paths.completion(source).unlink()
    if continuation == "retry":
        lab.store.close_activation(rework, Outcome.ERROR_TRANSPORT)
    else:
        register_lab_catalog_session(lab, rework)
        lab.steer(rework, reason="clarify", instructions="keep the evidence")
    successor = lab.tick().dispatched
    assert successor is not None
    assert lab.store.reads.load_activation(successor).metadata.inputs == original


def test_legacy_completion_preserves_unknown_provenance() -> None:
    """Old host evidence retains check identity without invented output or provenance."""
    from workflow_interpreter.bdio.carriers import VerifyOutcome

    completion = CompletionEvidence(
        outcome=Outcome.FAIL_CODE,
        claimed_outcome=None,
        evidence=Evidence(
            verify=(
                VerifyOutcome(cmd="scripts/check", exit_code=2, script_digest="a" * 64),
            )
        ),
    )
    payload = json.loads(bounded_payload("root", "source", completion))
    check = payload["checks"][0]
    assert check["exit_code"] == 2
    assert check["output_tails"] == []
    assert check["provenance_ok"] is None and check["timed_out"] is None


@pytest.mark.parametrize("optional", [False])
def test_engine_source_must_be_optional(tmp_path: Path, optional: bool) -> None:
    """Authoring cannot promise that an engine failure source always exists."""
    from workflow_interpreter import GraphValidationError, load_graph

    graph = feedback_graph(tmp_path)
    graph.write_text(
        graph.read_text().replace("optional=true", f"optional={str(optional).lower()}")
    )
    with pytest.raises(GraphValidationError, match="optional"):
        load_graph(graph)


@pytest.mark.parametrize("forgery", ["entry", "other_source"])
def test_mint_rejects_feedback_without_the_actual_causal_predecessor(
    tmp_path: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
    forgery: str,
) -> None:
    """The typed mint boundary rejects a forged binding even on an existing key."""
    from workflow_interpreter.bdio import MintReason, MintRequest

    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=feedback_graph(tmp_path),
        verify=RED_IF_MARKER,
    )
    root = lab.instantiate()
    source = _implement(lab, _writes(RED_MARKER))
    target = lab.tick().dispatched
    assert target is not None
    activation = lab.store.reads.load_activation(target)
    inputs = activation.metadata.inputs
    if forgery == "other_source":
        binding = next(b for b in inputs if b.name == "verify_failure")
        assert binding.verify_failure is not None
        proof = binding.verify_failure.model_copy(
            update={"source_activation_id": target}
        )
        forged = binding.model_copy(
            update={
                "verify_failure": proof,
                "producer_activation_id": target,
                "artifact_ref": proof.ref,
            }
        )
        inputs = tuple(forged if b.name == binding.name else b for b in inputs)
    request = MintRequest(
        node="implement",
        crew_profile=activation.metadata.crew_profile,
        model=activation.metadata.model,
        session_id="",
        mint_reason=MintReason.ENTRY if forgery == "entry" else MintReason.EDGE,
        predecessor_activation_id=None if forgery == "entry" else source,
        inputs=inputs,
    )
    with pytest.raises(CarrierIntegrityError, match="causal host failure"):
        lab.store.mint_activation(root.root_id, request)


def test_payload_digest_detects_replaced_blob_even_when_ref_matches(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """OID lookup alone cannot authenticate a rewritten payload against its binding."""
    from workflow_interpreter.inspector.gitcmd import GitSubcommand

    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=feedback_graph(tmp_path),
        verify=RED_IF_MARKER,
    )
    root = lab.instantiate()
    source_id = _implement(lab, _writes(RED_MARKER))
    target = lab.tick().dispatched
    assert target is not None
    binding = next(
        b
        for b in lab.store.reads.load_activation(target).metadata.inputs
        if b.name == "verify_failure"
    )
    source = lab.store.reads.load_activation(source_id)
    data = json.loads(materialize(lab.git, lab.repo, root, binding, source).text)
    data["checks"][0]["exit_code"] = 99
    file = tmp_path / "tampered.json"
    file.write_text(json.dumps(data))
    oid = lab.git.run(
        GitSubcommand.HASH_OBJECT, "-w", "--no-filters", "--", str(file), cwd=lab.repo
    ).text
    assert binding.verify_failure is not None
    proof = binding.verify_failure.model_copy(update={"blob_oid": oid})
    lab.git.update_ref(proof.ref, oid, cwd=lab.repo)
    binding = binding.model_copy(update={"verify_failure": proof})
    with pytest.raises(InputsUnavailable, match="causal host failure"):
        materialize(lab.git, lab.repo, root, binding, source)


@pytest.mark.parametrize("boundary", ["blob", "ref"])
def test_optional_pin_creation_failure_degrades_with_visible_deviation(
    tmp_path: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    """A failed initial pin leaves a dispatchable, auditable optional omission."""
    from workflow_interpreter.foreman import __main__ as main_module
    from workflow_interpreter.inspector.gitcmd import GitResult, GitSubcommand
    from workflow_interpreter.inspector.gitio import Git

    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=feedback_graph(tmp_path),
        verify=RED_IF_MARKER,
    )
    root = lab.instantiate()
    _implement(lab, _writes(RED_MARKER))
    original = Git.run

    def fail_pin(
        self: Git,
        command: GitSubcommand,
        *args: str,
        cwd: Path,
        check: bool = True,
        env: Mapping[str, str] | None = None,
        config: Sequence[str] = (),
    ) -> GitResult:
        """Fail only the optional feedback write at the Git boundary."""
        if (
            boundary == "blob"
            and command is GitSubcommand.HASH_OBJECT
            or boundary == "ref"
            and command is GitSubcommand.UPDATE_REF
            and any("/verify-failure/" in arg for arg in args)
        ):
            raise OSError("injected pin write failure")
        return original(
            self, command, *args, cwd=cwd, check=check, env=env, config=config
        )

    monkeypatch.setattr(Git, "run", fail_pin)
    report = lab.tick()
    assert report.stalled is None and report.opened_gate is None
    assert report.dispatched is not None
    activation = lab.store.reads.load_activation(report.dispatched)
    assert not any(b.name == "verify_failure" for b in activation.metadata.inputs)
    deviation = next(
        d
        for d in activation.metadata.deviations
        if d.kind == "verify_feedback_unpinned"
    )
    assert "injected pin write failure" in deviation.reason
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    assert "verify_feedback_unpinned" in transcript
