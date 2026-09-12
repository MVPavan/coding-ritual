"""Bounded independent roots; all durable coordination remains in Beads."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

if TYPE_CHECKING:
    from workflow_interpreter.schema.decisions import MemberAdmission

from workflow_interpreter.bdio.errors import BdioError
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.schema.decisions import (
    CancellationReceipt,
    ChildCoordinationView,
    ChildRecord,
    CollectedChildResult,
    CoordinationError,
)
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.errors import LockUnavailable, SupervisorError
from workflow_interpreter.supervisor.models import LaunchReceipt, LaunchReceiptState
from workflow_interpreter.supervisor.paths import ExecLedger, read_record, write_record


def finish_cancel(
    composition: Composition, owner: str, row: ChildRecord
) -> CancellationReceipt:
    coordinator = composition.store.coordination_store(composition=composition)
    assert row.cancellation is not None
    if row.cancellation.state == "cancelled":
        record_late_evidence(composition, row.root_id)
        return row.cancellation
    evidence: list[str] = []
    pending = False
    try:
        members = [
            row.root_id,
            *(
                r.decision_root_id
                for r in coordinator.state(owner).requests.values()
                if r.boundary.root_id == row.root_id and r.decision_root_id is not None
            ),
        ]
        for root_id in members:
            wiring = composition.for_root(root_id)
            with BandLock(coordinator.member_lock_path(root_id, "launch")):
                for activation in wiring.store.reads.list_activations(root_id):
                    handle = activation.metadata.handle
                    receipt_path = wiring.paths.receipt(activation.activation_id)
                    receipt = read_record(receipt_path, LaunchReceipt)
                    if handle is None and receipt is not None:
                        if (receipt.root_id, receipt.activation_id) != (
                            root_id,
                            activation.activation_id,
                        ):
                            raise CoordinationError("launch receipt identity mismatch")
                        handle = receipt.handle
                        # A receipt precedes exec; only its matching ledger proves
                        # a completed launch whose dispatch publication was lost.
                        ledger = ExecLedger(
                            wiring.paths.ledger(activation.activation_id)
                        )
                        if (
                            receipt.state is LaunchReceiptState.STARTED
                            and ledger.has_launch(receipt.launch_id)
                        ):
                            wiring.store.record_dispatch(
                                activation.activation_id, handle
                            )
                    if handle is None:
                        if (
                            wiring.paths.ledger(activation.activation_id).exists()
                            or receipt_path.exists()
                            or activation.metadata.lifecycle.value != "minted"
                        ):
                            pending = True
                            row = row.model_copy(
                                update={
                                    "attention": "launch publication lacks a process identity; preserve ledger and receipts for reconciliation",
                                    "attention_source": "runtime",
                                }
                            )
                        continue
                    proof = procfs.terminate(
                        composition.supervisor_config, handle, composition.clock
                    )
                    write_record(
                        wiring.paths.activation_dir(activation.activation_id)
                        / "cancellation.json",
                        proof,
                    )
                    evidence.append(
                        f"wf-activation://{activation.activation_id}/cancellation"
                    )
                    if not proof.confirmed_dead:
                        pending = True
    except (
        CoordinationError,
        ValidationError,
        SupervisorError,
        BdioError,
        OSError,
    ) as exc:
        pending = True
        row = row.model_copy(
            update={"attention": str(exc)[:2048], "attention_source": "runtime"}
        )
    assert row.cancellation is not None
    result = row.cancellation.model_copy(
        update={
            "state": "cancel_pending" if pending else "cancelled",
            "evidence": tuple(evidence),
        }
    )
    try:
        coordinator.update_child(
            owner,
            row.model_copy(update={"state": result.state, "cancellation": result}),
        )
    except LockUnavailable:
        # The cancellation intent already fences dispatch. A competing driver
        # may briefly own the owner lock; recovery publishes process evidence.
        return row.cancellation
    record_late_evidence(composition, row.root_id)
    return result


def recover(
    composition: Composition, owner: str, row: ChildRecord
) -> ChildCoordinationView:
    coordinator = composition.store.coordination_store(composition=composition)
    if row.cancellation is not None:
        finish_cancel(composition, owner, row)
    elif row.collection is None:
        from workflow_interpreter.foreman.tick import Foreman

        if row.attention_source == "runtime":
            coordinator.update_child(
                owner,
                row.model_copy(
                    update={
                        "attention": None,
                        "attention_source": None,
                    }
                ),
            )
        Foreman(composition).tick(row.root_id)
        current = coordinator.child_record(owner, row.slot, row.generation)
        coordinator.update_child(owner, observe(composition, current))
    return coordinator.child_status(owner)


def collect(
    composition: Composition, owner: str, row: ChildRecord
) -> CollectedChildResult:
    from workflow_interpreter.bdio import Lifecycle, Outcome
    from workflow_interpreter.schema.decisions import digest_record

    coordinator = composition.store.coordination_store(composition=composition)
    # Owner-before-member for the final immutable receipt transition.
    with (
        coordinator._locked(owner),
        BandLock(coordinator.member_lock_path(row.root_id)),
    ):
        row = coordinator.child_record(owner, row.slot, row.generation)
        if row.cancellation is not None:
            raise CoordinationError("cancelled child cannot collect")
        if row.collection is not None:
            return row.collection
        wiring = composition.for_root(row.root_id)
        root = wiring.store.reads.load_root(row.root_id)
        terminal = root.metadata.terminal
        activations = wiring.store.reads.list_activations(row.root_id)
        latest = max(activations, key=lambda a: a.metadata.seq, default=None)
        gates = wiring.store.reads.list_gates(row.root_id)
        if (
            not terminal
            or root.bead.status != "closed"
            or latest is None
            or latest.metadata.lifecycle is not Lifecycle.CLOSED
            or any(g.bead.status != "closed" for g in gates)
        ):
            raise CoordinationError("child is not settled")
        if (
            terminal == root.definition.document.fallback.to
            or latest.metadata.outcome
            not in (Outcome.DONE, Outcome.ACCEPT, Outcome.NO_DIFF)
            or any(g.metadata.outcome == Outcome.ABANDON for g in gates)
        ):
            raise CoordinationError(
                f"child settled unsuccessfully at {terminal}; evidence {latest.activation_id}"
            )
        evidence = latest.metadata.evidence
        if (
            evidence is None
            or not evidence.outputs_ref
            or not evidence.outputs_tree_oid
            or not root.metadata.instance_base_commit
        ):
            raise CoordinationError("settled child lacks immutable artifact evidence")
        output_commit = composition.git.ref_target(
            evidence.outputs_ref, cwd=wiring.repo_root
        )
        artifact = evidence.artifact
        from typing import Literal

        artifact_source: Literal["computed-output", "activation-input"] = (
            "computed-output"
        )
        if artifact is None:
            from workflow_interpreter.bdio import ArtifactIdentity
            from workflow_interpreter.foreman.execution import resolved_node

            if resolved_node(root, latest.metadata.node).node.writes:
                raise CoordinationError(
                    "writer lacks computed repository artifact evidence"
                )
            # A reader produces outputs, not a new repository artifact. Name the
            # immutable activation input that was actually dispatched, never HEAD.
            commit = latest.metadata.intended_base_commit
            artifact = ArtifactIdentity(
                commit_oid=commit,
                tree_oid=composition.git.tree_oid(commit, cwd=wiring.repo_root),
            )
            artifact_source = "activation-input"
        if (
            output_commit is None
            or composition.git.tree_oid(output_commit, cwd=wiring.repo_root)
            != evidence.outputs_tree_oid
            or composition.git.tree_oid(artifact.commit_oid, cwd=wiring.repo_root)
            != artifact.tree_oid
        ):
            raise CoordinationError(
                "child output/artifact tree disagrees with evidence"
            )
        result = CollectedChildResult(
            root_id=row.root_id,
            slot=row.slot,
            generation=row.generation,
            terminal=terminal,
            activation_id=latest.activation_id,
            graph_hash=root.definition.content_hash,
            config_signature=root.metadata.config_signature,
            base_commit=root.metadata.instance_base_commit,
            outputs_ref=evidence.outputs_ref,
            outputs_commit=output_commit,
            outputs_tree=evidence.outputs_tree_oid,
            artifact_commit=artifact.commit_oid,
            artifact_tree=artifact.tree_oid,
            artifact_source=artifact_source,
            evidence_digest=digest_record(evidence),
        )
        result = result.model_copy(update={"receipt_digest": digest_record(result)})
        state = coordinator.state(owner)
        coordinator._save(
            state.model_copy(
                update={
                    "children": {
                        **state.children,
                        row.slot: row.model_copy(
                            update={
                                "state": "collected",
                                "collection": result,
                                "activation_id": latest.activation_id,
                                "session_id": latest.metadata.session_id,
                                "pid": latest.metadata.handle.pid
                                if latest.metadata.handle
                                else None,
                                "proc_start_time": latest.metadata.handle.proc_start_time
                                if latest.metadata.handle
                                else None,
                            }
                        ),
                    }
                }
            )
        )
        return result


def observe(composition: Composition, row: ChildRecord) -> ChildRecord:
    """Bounded evidence pointers from authoritative local lifecycle reads."""
    if row.cancellation is not None or row.collection is not None:
        return row
    root = composition.store.reads.load_root(row.root_id)
    activations = composition.store.reads.list_activations(row.root_id)
    latest = max(activations, key=lambda a: a.metadata.seq, default=None)
    gates = composition.store.reads.list_gates(row.root_id)
    waiting = next((g for g in gates if g.bead.status != "closed"), None)
    changes: dict[str, object] = {
        "terminal": root.metadata.terminal,
        "state": "settled"
        if root.metadata.terminal
        else "running"
        if latest
        else "admitted",
        "attention": f"waiting at gate {waiting.gate_id}"
        if waiting
        else None
        if (row.attention or "").startswith("waiting at gate ")
        else row.attention,
    }
    if latest is not None:
        changes.update(
            activation_id=latest.activation_id,
            outcome=latest.metadata.outcome,
            evidence_reference=f"wf-activation://{latest.activation_id}/evidence"
            if latest.metadata.evidence
            else None,
            process_reference=latest.activation_id if latest.metadata.handle else None,
            session_id=latest.metadata.session_id,
            pid=latest.metadata.handle.pid if latest.metadata.handle else None,
            proc_start_time=latest.metadata.handle.proc_start_time
            if latest.metadata.handle
            else None,
        )
    return row.model_copy(update=changes)


def drive(
    composition: Composition, owner: str, max_concurrent: int, max_wall_s: float
) -> ChildCoordinationView:
    import math
    import time

    from workflow_interpreter.foreman.tick import Foreman

    coordinator = composition.store.coordination_store(composition=composition)
    count = len(coordinator.child_status(owner).children)
    if type(max_concurrent) is not int or not 1 <= max_concurrent <= count:
        raise CoordinationError(
            "concurrency must be between 1 and admitted child count"
        )
    if isinstance(max_wall_s, bool) or not math.isfinite(max_wall_s) or max_wall_s <= 0:
        raise CoordinationError("max_wall_s must be finite and positive")
    contended: set[str] = set()
    deadline = time.monotonic() + max_wall_s
    # Independent drivers share this session exclusion, never the metadata lock.
    with BandLock(coordinator.member_lock_path(owner, "drive")):
        while time.monotonic() < deadline:
            rows = [
                observe(composition, r)
                for r in coordinator.child_status(owner).children
            ]
            active = active_slots(composition, owner, rows)
            if len(active) > max_concurrent:
                raise CoordinationError(
                    "existing active children exceed requested concurrency"
                )
            eligible = False
            for row in rows:
                if time.monotonic() >= deadline:
                    break
                if row.cancellation is not None or row.collection is not None:
                    continue
                if row.slot not in active and len(active) >= max_concurrent:
                    eligible = True
                    continue
                try:
                    if row.state == "settled" or (
                        row.attention
                        and not row.attention.startswith("waiting at gate ")
                    ):
                        coordinator.update_child(owner, row)
                        continue
                    composition.for_root(row.root_id)
                    eligible = True
                    report = Foreman(composition).tick(row.root_id)
                    if report.contended:
                        contended.add(row.slot)
                    current = coordinator.child_record(owner, row.slot, row.generation)
                    updated = observe(composition, current)
                    if (
                        updated.attention_source != "decision"
                        and (report.stalled or report.halted or report.refusals)
                        and not (updated.attention or "").startswith("waiting at gate ")
                    ):
                        updated = updated.model_copy(
                            update={
                                "attention": (
                                    report.stalled
                                    or "; ".join(report.refusals)
                                    or "halted"
                                )[:2048],
                                "attention_source": "runtime",
                            }
                        )
                    coordinator.update_child(owner, updated)
                    active = active_slots(composition, owner, rows)
                except LockUnavailable:
                    contended.add(row.slot)
                    # A short metadata collision cannot be recorded while its lock is held.
                    # Retry only inside this driver's finite deadline.
                    eligible = True
                except (
                    CoordinationError,
                    ValidationError,
                    OSError,
                    BdioError,
                    SupervisorError,
                ) as exc:
                    current = coordinator.child_record(owner, row.slot, row.generation)
                    try:
                        coordinator.update_child(
                            owner,
                            current.model_copy(
                                update={
                                    "attention": str(exc)[:2048],
                                    "attention_source": "runtime",
                                }
                            ),
                        )
                    except LockUnavailable:
                        eligible = True
            if not eligible:
                return coordinator.child_status(owner).model_copy(
                    update={
                        "timed_out": time.monotonic() >= deadline,
                        "contended_slots": tuple(sorted(contended)),
                    }
                )
            time.sleep(min(0.02, max(0, deadline - time.monotonic())))
    return coordinator.child_status(owner).model_copy(
        update={"timed_out": True, "contended_slots": tuple(sorted(contended))}
    )


def checked_admission(
    composition: Composition,
    graph: Path,
    slot: str,
    inputs: Mapping[str, Path],
) -> MemberAdmission:
    """Resolve the normal graph/config/input contract without creating a root."""
    from pydantic import TypeAdapter

    from workflow_interpreter.bdio import InstanceInput, ResolvedSetting
    from workflow_interpreter.foreman.resolve import (
        _pinned_instance_inputs,
        _resolved_config,
    )
    from workflow_interpreter.schema.decisions import DecisionTemplate, MemberAdmission
    from workflow_interpreter.schema.loader import canonical_bytes, load_graph

    definition = load_graph(graph)
    missing = {
        node.runner.removeprefix("profile:")
        for node in definition.document.node
        if node.runner and node.runner.startswith("profile:")
    } - set(composition.config.roles)
    if missing:
        raise CoordinationError("unknown runner roles: " + ", ".join(sorted(missing)))
    pinned = _pinned_instance_inputs(definition, inputs, allow_test_flags=False)
    settings = _resolved_config(composition, definition, {})
    return MemberAdmission(
        graph_body=canonical_bytes(definition.document).decode(),
        config_json=TypeAdapter(tuple[ResolvedSetting, ...])
        .dump_json(settings)
        .decode(),
        inputs_json=TypeAdapter(tuple[InstanceInput, ...]).dump_json(pinned).decode(),
        base_commit=composition.git.head_commit(cwd=composition.config.repo_root),
        slot=slot,
        generation=0,
        templates={
            s.key.split(".")[1]: DecisionTemplate.model_validate_json(str(s.value))
            for s in settings
            if s.key.startswith("decision.") and s.key.endswith(".template")
        },
    )


def command(composition: Composition, args: object) -> str:
    """Six parser forms; admission files carry validated pins, not instructions."""
    from argparse import Namespace

    from workflow_interpreter.schema.decisions import MemberAdmission

    if not isinstance(args, Namespace):
        raise CoordinationError("invalid child command")
    coordinator = composition.store.coordination_store(composition=composition)
    name = args.child_command
    if name == "replace":
        from workflow_interpreter.foreman.replacement import replace_checked
        from workflow_interpreter.schema.decisions import TrustedReplacementRequest

        with args.request.open("rb") as stream:
            body = stream.read(1_048_577)
        if len(body) > 1_048_576:
            raise CoordinationError("replacement request exceeds 1 MiB")
        return replace_checked(
            composition,
            args.owner_id,
            args.slot,
            args.generation,
            TrustedReplacementRequest.model_validate_json(body),
        ).model_dump_json()
    if name == "admit":
        import json

        from workflow_interpreter.foreman.__main__ import _instance_inputs
        from workflow_interpreter.schema.decisions import digest_record

        admission = checked_admission(
            composition, args.graph, args.slot, _instance_inputs(args.input)
        )
        receipt = coordinator.start_child(args.owner_id, args.slot, admission)
        root = composition.store.reads.load_root(receipt.root_id)
        return json.dumps(
            {
                "receipt": receipt.model_dump(mode="json"),
                "admission_digest": digest_record(admission),
                "graph_hash": root.definition.content_hash,
                "config_signature": root.metadata.config_signature,
            }
        )
    if name == "start":
        with args.admission.open("rb") as stream:
            body = stream.read(1_048_577)
        if len(body) > 1_048_576:
            raise CoordinationError("child admission exceeds 1 MiB")
        from pydantic import TypeAdapter

        from workflow_interpreter.bdio import ResolvedSetting
        from workflow_interpreter.foreman.resolve import _resolved_config
        from workflow_interpreter.schema.decisions import digest_record
        from workflow_interpreter.schema.loader import load_pinned_body

        admission = MemberAdmission.model_validate_json(body)
        reserved = coordinator.state(args.owner_id).reservations.get(
            digest_record(admission)
        )
        if reserved is None:
            definition = load_pinned_body(admission.graph_body.encode())
            resolved = _resolved_config(composition, definition, {})
            supplied = TypeAdapter(tuple[ResolvedSetting, ...]).validate_json(
                admission.config_json
            )
            expected = {s.key: s for s in resolved}
            # Historical unused decision templates grant no authority in a graph
            # without that policy. Active templates must still match resolution.
            actual = {
                s.key: s
                for s in supplied
                if not s.key.startswith("decision.") or s.key in expected
            }
            if actual != expected:
                raise CoordinationError(
                    "raw child admission pins differ from resolved configuration"
                )
        elif reserved.admission != admission:
            raise CoordinationError("raw child admission differs from saved pins")
        result = coordinator.start_child(args.owner_id, args.slot, admission)
        return result.model_dump_json()
    if name == "status":
        return coordinator.child_status(args.owner_id).model_dump_json()
    if name == "drive":
        return coordinator.drive_children(
            args.owner_id, args.max_concurrent, args.max_wall
        ).model_dump_json()
    if name == "cancel":
        return coordinator.cancel_child(
            args.owner_id, args.slot, args.generation, args.request_key, args.reason
        ).model_dump_json()
    if name == "collect":
        return coordinator.collect_child(
            args.owner_id, args.slot, args.generation
        ).model_dump_json()
    return coordinator.recover_child(
        args.owner_id, args.slot, args.generation
    ).model_dump_json()


def record_late_evidence(composition: Composition, root_id: str) -> None:
    """Cancellation blocks authority, not immutable evidence publication."""
    from workflow_interpreter.bdio import Lifecycle
    from workflow_interpreter.supervisor.models import CompletionEvidence

    root = composition.store.reads.load_root(root_id)
    link = root.metadata.coordination
    if link is None:
        return
    row = composition.store.coordination_store().child_for_root(root)
    if row is None or row.cancellation is None:
        return
    wiring = composition.for_root(root_id)
    for activation in wiring.store.reads.list_activations(root_id):
        if activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED:
            completion = read_record(
                wiring.paths.completion(activation.activation_id), CompletionEvidence
            )
            if completion is not None:
                wiring.store.record_evidence(
                    activation.activation_id, completion.evidence
                )


def active_slots(
    composition: Composition, owner: str, rows: list[ChildRecord]
) -> set[str]:
    """Count launch intents too, including decision tasks and pending cancellation."""
    from workflow_interpreter.bdio import Lifecycle

    state = composition.store.coordination_store().state(owner)
    active: set[str] = set()
    for row in rows:
        if row.state in ("cancelled", "collected"):
            continue
        members = [
            row.root_id,
            *(
                r.decision_root_id
                for r in state.requests.values()
                if r.boundary.root_id == row.root_id and r.decision_root_id is not None
            ),
        ]
        if any(
            a.metadata.lifecycle in (Lifecycle.MINTED, Lifecycle.DISPATCHED)
            for root_id in members
            for a in composition.store.reads.list_activations(root_id)
        ):
            active.add(row.slot)
    return active
