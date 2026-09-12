"""Original-owner durable successors preserve existing authority."""

from pathlib import Path

import pytest

from tests.test_children_process import writer_lab
from workflow_interpreter.foreman.decisions import admission_of
from workflow_interpreter.foreman.replacement import replace_checked
from workflow_interpreter.schema.decisions import (
    CoordinationError,
    TrustedReplacementRequest,
)


def test_trusted_successor_without_ship_preserves_owner_and_replays(
    tmp_path: Path,
) -> None:
    lab, owner, composition, _ = writer_lab(tmp_path)
    store = lab.store.coordination_store(composition=composition)
    old = store.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    graph = tmp_path / "writer.toml"
    graph.write_text(
        graph.read_text().replace(
            "Write the deterministic feature", "Implement the deterministic feature"
        )
    )
    request = TrustedReplacementRequest(
        request_key="change", reason="correct instructions", graph=str(graph)
    )
    new = replace_checked(composition, owner.root_id, "one", 0, request)
    assert new.root_id != old.root_id
    assert new.link.owner_id == owner.root_id
    assert new.link.predecessor_id == old.root_id
    assert replace_checked(composition, owner.root_id, "one", 0, request) == new
    assert store.child_record(owner.root_id, "one", 1).root_id == new.root_id
    with pytest.raises(CoordinationError, match="payload"):
        replace_checked(
            composition,
            owner.root_id,
            "one",
            0,
            request.model_copy(update={"reason": "changed"}),
        )


def test_write_scope_change_is_refused_before_fencing(tmp_path: Path) -> None:
    lab, owner, composition, _ = writer_lab(tmp_path)
    graph = tmp_path / "writer.toml"
    graph.write_text(graph.read_text().replace('"src/**"', '"other/**"'))
    with pytest.raises(CoordinationError, match="obligations"):
        replace_checked(
            composition,
            owner.root_id,
            "work",
            0,
            TrustedReplacementRequest(
                request_key="bad", reason="scope", graph=str(graph)
            ),
        )
    assert (
        lab.store.coordination_store().state(owner.root_id).active["work"]
        == owner.root_id
    )


@pytest.mark.parametrize("boundary", ["reservation", "intent", "root", "receipt"])
def test_successor_crash_replays_one_root(
    tmp_path: Path, monkeypatch, boundary: str
) -> None:
    from workflow_interpreter.bdio.coordination import CoordinationStore
    from workflow_interpreter.foreman import replacement

    lab, owner, composition, _ = writer_lab(tmp_path)
    request = TrustedReplacementRequest(
        request_key="repair", reason="repair", graph=str(tmp_path / "writer.toml")
    )
    original = {
        "root": CoordinationStore.admit_member,
        "reservation": CoordinationStore._reserve,
    }.get(boundary, replacement._save)
    tripped = False

    def crash(*args, **kwargs):
        nonlocal tripped
        result = original(*args, **kwargs)
        hit = boundary in ("root", "reservation") or (
            args[1].receipt is not None
            if boundary == "receipt"
            else args[1].receipt is None
        )
        if hit and not tripped:
            tripped = True
            raise RuntimeError("crash after durable write")
        return result

    if boundary in ("root", "reservation"):
        monkeypatch.setattr(
            CoordinationStore,
            "admit_member" if boundary == "root" else "_reserve",
            crash,
        )
    else:
        monkeypatch.setattr(replacement, "_save", crash)
    with pytest.raises(RuntimeError, match="crash"):
        replace_checked(composition, owner.root_id, "work", 0, request)
    result = replace_checked(composition, owner.root_id, "work", 0, request)
    state = lab.store.coordination_store().state(owner.root_id)
    assert len(state.reservations) == 2
    assert state.active["work"] == result.root_id
    assert state.successors["repair"].receipt == result


def test_p2_child_updates_current_slot_and_matching_decision_replays(
    tmp_path: Path, monkeypatch
) -> None:
    from tests._supervisor import ChildScript
    from tests.test_children_lifecycle import owner_lab
    from workflow_interpreter.foreman import replacement
    from workflow_interpreter.foreman.decisions import reconcile_action

    lab, owner = owner_lab(tmp_path)
    store = lab.store.coordination_store(composition=lab.composition)
    old = store.start_child(
        owner,
        "child",
        admission_of(lab.store.reads.load_root(owner), slot="child", generation=0),
    )
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "replace"
    # Crash after the successor is admitted but before P2 marks consumption applied.
    original = replacement.advance_successor

    def crash(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("after admission")

    monkeypatch.setattr(replacement, "advance_successor", crash)
    with pytest.raises(RuntimeError, match="after admission"):
        for _ in range(20):
            lab.foreman.tick(old.root_id)
    monkeypatch.setattr(replacement, "advance_successor", original)
    state = store.state(owner)
    decision = next(
        r for r in state.requests.values() if r.boundary.root_id == old.root_id
    )
    assert decision.state == "consumed"
    result = reconcile_action(lab.composition, owner, decision.request_id)
    assert result.applied
    new = store.child_record(owner, "child", 1)
    assert new.root_id == result.replacement_id != old.root_id
    assert new.root_id == store.state(owner).active["child"]
    assert (
        lab.store.reads.load_root(new.root_id).definition.content_hash
        == lab.store.reads.load_root(old.root_id).definition.content_hash
    )
    assert reconcile_action(lab.composition, owner, decision.request_id) == result


@pytest.mark.parametrize("fence", ["cancel", "gate", "budget", "artifact"])
def test_successor_authority_refusals_preserve_predecessor(
    tmp_path: Path, fence: str
) -> None:
    import subprocess

    from workflow_interpreter.foreman.gates import halt_gate
    from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF

    lab, owner, composition, _ = writer_lab(tmp_path)
    store = lab.store.coordination_store(composition=composition)
    child = store.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    if fence == "cancel":
        store.cancel_child(owner.root_id, "one", 0, "cancel", "stop")
    elif fence == "gate":
        wiring = composition.for_root(child.root_id)
        with wiring.band:
            wiring.store.open_gate(child.root_id, halt_gate("attention"))
    elif fence == "budget":
        for slot in ("two", "three", "four"):
            store.start_child(
                owner.root_id, slot, admission_of(owner, slot=slot, generation=0)
            )
    else:
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "foreign commit"],
            cwd=lab.repo,
            check=True,
            capture_output=True,
        )
        lab.git.update_ref(
            INSTANCE_BRANCH_REF.format(root_id=child.root_id),
            lab.git.head_commit(cwd=lab.repo),
            cwd=lab.repo,
        )
    request = TrustedReplacementRequest(
        request_key="refuse", reason="guard", graph=str(tmp_path / "writer.toml")
    )
    with pytest.raises(CoordinationError):
        replace_checked(composition, owner.root_id, "one", 0, request)
    assert store.state(owner.root_id).active["one"] == child.root_id
    assert not store.state(owner.root_id).successors


@pytest.mark.bd
def test_real_beads_successor_intent_receipt_roundtrip(
    tmp_path: Path, bd_config
) -> None:
    from dataclasses import replace

    from workflow_interpreter.bdio import WorkflowStore
    from workflow_interpreter.bdio.client import BdClient
    from workflow_interpreter.foreman.resolve import instantiate

    lab, _, composition, _ = writer_lab(tmp_path)
    store = WorkflowStore(BdClient(bd_config))
    composition = replace(
        composition,
        store=store,
        config=composition.config.model_copy(update={"bd": bd_config}),
    )
    owner = instantiate(
        composition,
        lab._toml,
        instance_key="p5-successor-" + tmp_path.name,
        instance_inputs={},
        allow_test_flags=False,
        overrides={},
    )
    request = TrustedReplacementRequest(
        request_key="durable", reason="new instructions", graph=str(lab._toml)
    )
    receipt = replace_checked(composition, owner.root_id, "work", 0, request)
    # A fresh client reads the actual Beads journal; no in-memory receipt cache.
    restarted = replace(composition, store=WorkflowStore(BdClient(bd_config)))
    assert replace_checked(restarted, owner.root_id, "work", 0, request) == receipt
    state = restarted.store.coordination_store().state(owner.root_id)
    assert state.successors["durable"].receipt == receipt
    assert len(state.reservations) == 2


def test_concurrent_successor_requests_converge_same_reservation(
    tmp_path: Path,
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from workflow_interpreter.supervisor.errors import LockUnavailable

    lab, owner, composition, _ = writer_lab(tmp_path)
    request = TrustedReplacementRequest(
        request_key="race", reason="same", graph=str(tmp_path / "writer.toml")
    )
    barrier = Barrier(2)

    def attempt():
        barrier.wait(timeout=5)
        try:
            return replace_checked(composition, owner.root_id, "work", 0, request)
        except LockUnavailable:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    final = replace_checked(composition, owner.root_id, "work", 0, request)
    assert all(result is None or result == final for result in results)
    assert len(lab.store.coordination_store().state(owner.root_id).reservations) == 2


def test_trusted_model_change_pins_new_config_without_changing_predecessor(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    lab, owner, composition, _ = writer_lab(tmp_path)
    old = owner.metadata.model_dump_json()
    roles = composition.config.roles
    changed = replace(
        composition,
        config=composition.config.model_copy(
            update={
                "roles": {
                    **roles,
                    "implementer": roles["implementer"].model_copy(
                        update={"model": "different-model"}
                    ),
                }
            }
        ),
    )
    request = TrustedReplacementRequest(
        request_key="model", reason="new model", graph=str(tmp_path / "writer.toml")
    )
    receipt = replace_checked(changed, owner.root_id, "work", 0, request)
    successor = lab.store.reads.load_root(receipt.root_id)
    assert replace_checked(composition, owner.root_id, "work", 0, request) == receipt
    assert successor.metadata.config_signature != owner.metadata.config_signature
    assert successor.definition.content_hash == owner.definition.content_hash
    assert (
        lab.store.reads.load_root(owner.root_id).metadata.resolved_config
        == owner.metadata.resolved_config
    )
    # Owner coordination journal grows, but its executable pins never change.
    assert "different-model" not in old


@pytest.mark.parametrize("changed_field", [None, "reason", "graph", "inputs"])
def test_saved_trusted_replay_without_graph_uses_request_digest(
    tmp_path: Path, monkeypatch, capsys, changed_field: str | None
) -> None:
    from workflow_interpreter.foreman import __main__ as cli

    lab, owner, composition, _ = writer_lab(tmp_path)
    graph = tmp_path / "writer.toml"
    request = TrustedReplacementRequest(
        request_key="saved", reason="original", graph=str(graph)
    )
    receipt = replace_checked(composition, owner.root_id, "work", 0, request)
    graph.unlink()
    if changed_field is None:
        assert (
            replace_checked(composition, owner.root_id, "work", 0, request) == receipt
        )
        request_file = tmp_path / "request.json"
        request_file.write_text(request.model_dump_json())
        monkeypatch.setattr(cli, "_composition", lambda _: composition)
        capsys.readouterr()
        assert (
            cli.main(
                [
                    "children",
                    "replace",
                    owner.root_id,
                    "--slot",
                    "work",
                    "--generation",
                    "0",
                    "--request",
                    str(request_file),
                ]
            )
            == 0
        )
        assert capsys.readouterr().out.strip() == receipt.model_dump_json()
    else:
        changes = {
            "reason": "changed",
            "graph": "missing-other.toml",
            "inputs": {"other": "missing.txt"},
        }
        with pytest.raises(CoordinationError, match="payload changed"):
            replace_checked(
                composition,
                owner.root_id,
                "work",
                0,
                request.model_copy(update={changed_field: changes[changed_field]}),
            )
    assert len(lab.store.coordination_store().state(owner.root_id).reservations) == 2


@pytest.mark.parametrize("identity", ["owner", "slot", "generation"])
def test_saved_trusted_replay_checks_cli_identity(
    tmp_path: Path, monkeypatch, capsys, identity: str
) -> None:
    from workflow_interpreter.foreman import __main__ as cli

    lab, owner, composition, _ = writer_lab(tmp_path)
    request = TrustedReplacementRequest(
        request_key="identity", reason="original", graph=str(tmp_path / "writer.toml")
    )
    replace_checked(composition, owner.root_id, "work", 0, request)
    store = lab.store.coordination_store(composition=composition)
    state = store.state(owner.root_id)
    slot, generation = (
        ("wrong", 0)
        if identity == "slot"
        else ("work", 1 if identity == "generation" else 0)
    )
    if identity == "owner":
        # A misplaced journal must not let a CLI owner claim another owner's receipt.
        saved = state.successors[request.request_key].model_copy(
            update={"owner_id": "different-owner"}
        )
        with store._locked(owner.root_id):
            store._save(
                state.model_copy(update={"successors": {request.request_key: saved}})
            )
    (tmp_path / "writer.toml").unlink()
    with pytest.raises(CoordinationError, match="scope"):
        replace_checked(composition, owner.root_id, slot, generation, request)
    request_file = tmp_path / "request.json"
    request_file.write_text(request.model_dump_json())
    monkeypatch.setattr(cli, "_composition", lambda _: composition)
    capsys.readouterr()
    assert (
        cli.main(
            [
                "children",
                "replace",
                owner.root_id,
                "--slot",
                slot,
                "--generation",
                str(generation),
                "--request",
                str(request_file),
            ]
        )
        == 2
    )
    assert "scope" in capsys.readouterr().out


@pytest.mark.parametrize("slot", ["work", "child"])
def test_second_key_after_reservation_crash_cannot_poison_original(
    tmp_path: Path, monkeypatch, slot: str
) -> None:
    from workflow_interpreter.bdio.coordination import CoordinationStore
    from workflow_interpreter.foreman.resolve import instantiate

    lab, _, composition, _ = writer_lab(tmp_path)
    graph = tmp_path / "writer.toml"
    graph.write_text(
        graph.read_text().replace("max_replacements=1", "max_replacements=2")
    )
    owner = instantiate(
        composition,
        graph,
        instance_key="two-replacements",
        instance_inputs={},
        allow_test_flags=False,
        overrides={},
    )
    store = lab.store.coordination_store(composition=composition)
    if slot == "child":
        store.start_child(
            owner.root_id, slot, admission_of(owner, slot=slot, generation=0)
        )
    predecessor = store.state(owner.root_id).active[slot]
    request = TrustedReplacementRequest(
        request_key="original", reason="recover me", graph=str(graph)
    )
    reserve = CoordinationStore._reserve
    crashed = False

    def crash(*args, **kwargs):
        nonlocal crashed
        result = reserve(*args, **kwargs)
        if kwargs.get("successor") is not None and not crashed:
            crashed = True
            raise RuntimeError("after reservation")
        return result

    monkeypatch.setattr(CoordinationStore, "_reserve", crash)
    with pytest.raises(RuntimeError, match="after reservation"):
        replace_checked(composition, owner.root_id, slot, 0, request)
    before = store.state(owner.root_id)
    assert before.active[slot] == predecessor
    with pytest.raises(CoordinationError, match="original"):
        replace_checked(
            composition,
            owner.root_id,
            slot,
            0,
            request.model_copy(update={"request_key": "second"}),
        )
    assert store.state(owner.root_id) == before
    assert (
        sum(r.capacity.kind == "replacement" for r in before.reservations.values()) == 1
    )
    graph.unlink()
    receipt = replace_checked(composition, owner.root_id, slot, 0, request)
    recovered = store.state(owner.root_id)
    assert recovered.active[slot] == receipt.root_id
    assert set(recovered.successors) == {"original"}
    assert (
        sum(r.capacity.kind == "replacement" for r in recovered.reservations.values())
        == 1
    )
