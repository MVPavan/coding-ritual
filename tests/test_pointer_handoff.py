"""Reference-mode handoffs use pinned Git evidence at the real task seam."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._foreman import ForemanLab
from tests._foreman import entry_request as lab_entry_request
from tests._supervisor import (
    add_submodule,
    commit_all,
    make_config,
    make_git,
    make_repo,
)
from workflow_interpreter.bdio import Evidence, InputBinding, MintReason, Outcome
from workflow_interpreter.bdio.carriers import ArtifactIdentity
from workflow_interpreter.foreman.envelope import InputsUnavailable
from workflow_interpreter.foreman.evidence_export import (
    EXPORT_MAX_DIFF_BYTES,
    export_reference,
)
from workflow_interpreter.foreman.supervise import _task_builder
from workflow_interpreter.schema.loader import (
    GraphValidationError,
    canonical_bytes,
    load_graph,
    load_pinned_body,
)
from workflow_interpreter.schema.models import ArtifactInputMode, RuleId
from workflow_interpreter.supervisor import activation_ref, channels_for
from workflow_interpreter.supervisor.errors import GitCommandError, SandboxUnavailable
from workflow_interpreter.supervisor.sandbox import SandboxMode


def _references(root):
    definition = root.definition if hasattr(root, "definition") else root
    document = definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(
                    update={"artifact_input_mode": ArtifactInputMode.REFERENCES}
                )
                if node.name == "review"
                else node
                for node in definition.document.node
            )
        }
    )
    updated = definition.model_copy(
        update={
            "document": document,
            "content_hash": hashlib.sha256(canonical_bytes(document)).hexdigest(),
        }
    )
    return (
        root.model_copy(update={"definition": updated})
        if hasattr(root, "definition")
        else updated
    )


def _pinned_writer(fake_store, tmp_path: Path):
    repo = make_repo(tmp_path)
    git = make_git(make_config(repo, tmp_path))
    base = git.head_commit(cwd=repo)
    (repo / "source.txt").write_text("d" * (80 * 1024 + 1), encoding="utf-8")
    candidate = git.snapshot_commit(
        message="candidate",
        parents=(base,),
        index_path=tmp_path / "candidate.index",
        cwd=repo,
    )
    root = _references(make_root(fake_store, load_definition()))
    producer = fake_store.mint_activation(root.root_id, entry_request()).activation
    artifact_ref = activation_ref(root.root_id, producer.activation_id)
    git.update_ref(artifact_ref, candidate, cwd=repo)
    evidence = Evidence(
        artifact=ArtifactIdentity(
            commit_oid=candidate, tree_oid=git.tree_oid(candidate, cwd=repo)
        )
    )
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={"pre_attempt_commit": base, "evidence": evidence}
            )
        }
    )
    binding = InputBinding(
        name="diff_artifact",
        producer_activation_id=producer.activation_id,
        artifact_ref=artifact_ref,
        digest=evidence.artifact.tree_oid,
    )
    return repo, git, root, producer, binding


def _with_reports(producer, git, repo: Path, ref: str, commit: str):
    evidence = producer.metadata.evidence
    assert evidence is not None
    git.update_ref(ref, commit, cwd=repo)
    return producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "evidence": evidence.model_copy(
                        update={
                            "outputs_ref": ref,
                            "outputs_tree_oid": git.tree_oid(commit, cwd=repo),
                        }
                    )
                }
            )
        }
    )


def test_mode_is_task_only_and_absent_mode_keeps_legacy_canonical_bytes(
    feature_graph: Path, tmp_path: Path
) -> None:
    """Both graph generations omit the default mode from their pinned bytes."""
    definition = load_graph(feature_graph)
    body = canonical_bytes(definition.document)
    assert b"artifact_input_mode" not in body
    assert canonical_bytes(load_pinned_body(body).document) == body
    invalid = tmp_path / "invalid.toml"
    invalid.write_text(
        feature_graph.read_text(encoding="utf-8").replace(
            'name      = "ship"\nkind      = "gate"',
            'name      = "ship"\nkind      = "gate"\nartifact_input_mode = "references"',
        ),
        encoding="utf-8",
    )
    with pytest.raises(GraphValidationError) as error:
        load_graph(invalid)
    assert error.value.rule_ids == frozenset({RuleId.NODE_FIELDS_MATCH_KIND})


def test_task_builder_uses_compact_pointers_and_retains_instance_brief(
    tmp_path: Path,
) -> None:
    """The production builder, not the exporter alone, selects references mode."""
    lab = ForemanLab(
        tmp_path,
        sandbox=SandboxMode.OFF,
        instance_inputs={"task_brief": "original brief"},
    )
    lab.definition = _references(lab.definition)
    root = lab.instantiate()
    wiring = lab.wiring()
    base = lab.git.head_commit(cwd=lab.repo)
    (lab.repo / "source.txt").write_text("d" * (80 * 1024 + 1), encoding="utf-8")
    candidate = lab.git.snapshot_commit(
        message="candidate",
        parents=(base,),
        index_path=tmp_path / "candidate.index",
        cwd=lab.repo,
    )
    producer = wiring.store.mint_activation(
        root.root_id, lab_entry_request()
    ).activation
    artifact_ref = activation_ref(root.root_id, producer.activation_id)
    lab.git.update_ref(artifact_ref, candidate, cwd=lab.repo)
    evidence = Evidence(
        artifact=ArtifactIdentity(
            commit_oid=candidate, tree_oid=lab.git.tree_oid(candidate, cwd=lab.repo)
        )
    )
    lab.fake_bd.rows[producer.activation_id]["metadata"].update(
        {
            "pre_attempt_commit": base,
            "evidence": evidence.model_dump(mode="json"),
            "lifecycle": "closed",
            "outcome": Outcome.DONE.value,
        }
    )
    binding = InputBinding(
        name="diff_artifact",
        producer_activation_id=producer.activation_id,
        artifact_ref=artifact_ref,
        digest=evidence.artifact.tree_oid,
    )
    brief_input = root.metadata.instance_inputs[0]
    instance_binding = InputBinding(
        name="task_brief",
        producer_activation_id="instance",
        artifact_ref="wf-instance://task_brief",
        digest=brief_input.sha256,
    )
    review = wiring.store.mint_activation(
        root.root_id,
        lab_entry_request(
            node="review",
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=producer.activation_id,
            inputs=(instance_binding, binding),
        ),
    ).activation
    paths = wiring.paths
    paths.ensure_activation_dir(review.activation_id)
    task = _task_builder(root, wiring, lab.git)(
        review,
        channels_for(
            paths.activation_dir(review.activation_id), paths.log(review.activation_id)
        ),
    )
    assert len(task.brief.encode()) <= 32768
    assert "original brief" in task.brief
    assert "Inspect exported evidence before deciding" in task.brief
    assert '"index_path"' in task.brief
    assert "d" * 1024 not in task.brief
    assert task.artifact_input_mode is ArtifactInputMode.REFERENCES
    with pytest.raises(SandboxUnavailable, match="requires sandbox = bwrap"):
        wiring.supervisor._dispatcher._sandbox(review.activation_id, task)


def test_export_uses_pinned_objects_after_live_mutation(
    fake_store, tmp_path: Path
) -> None:
    repo, git, root, producer, binding = _pinned_writer(fake_store, tmp_path)
    activation = tmp_path / "activation"
    activation.mkdir()
    pointer = json.loads(
        export_reference(git, repo, activation, root, binding, producer)
    )
    index = json.loads(Path(pointer["index_path"]).read_text(encoding="utf-8"))
    (repo / "source.txt").write_text("live mutation", encoding="utf-8")
    assert "live mutation" not in Path(index["diff_path"]).read_text(encoding="utf-8")


def test_export_refuses_moved_pins_and_oversized_diff(
    fake_store, tmp_path: Path
) -> None:
    repo, git, root, producer, binding = _pinned_writer(fake_store, tmp_path)
    git.update_ref(binding.artifact_ref, git.head_commit(cwd=repo), cwd=repo)
    with pytest.raises(InputsUnavailable, match="pin"):
        export_reference(git, repo, tmp_path, root, binding, producer)
    huge = repo / "huge.txt"
    huge.write_bytes(b"x" * (EXPORT_MAX_DIFF_BYTES + 1))
    candidate = git.snapshot_commit(
        message="huge",
        parents=(git.head_commit(cwd=repo),),
        index_path=tmp_path / "huge.index",
        cwd=repo,
    )
    evidence = producer.metadata.evidence
    assert evidence is not None
    updated = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "pre_attempt_commit": git.head_commit(cwd=repo),
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid=candidate,
                            tree_oid=git.tree_oid(candidate, cwd=repo),
                        )
                    ),
                }
            )
        }
    )
    git.update_ref(binding.artifact_ref, candidate, cwd=repo)
    updated_binding = binding.model_copy(
        update={"digest": updated.metadata.evidence.artifact.tree_oid}
    )
    with pytest.raises(InputsUnavailable, match="export"):
        export_reference(git, repo, tmp_path, root, updated_binding, updated)


def test_export_rejects_unsafe_report_entries_and_rebuilds_stale_directory(
    fake_store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, git, root, producer, binding = _pinned_writer(fake_store, tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "report.txt").write_text("report", encoding="utf-8")
    report_commit = git.commit_directory(
        ("report.txt",),
        root=reports,
        message="reports",
        index_path=tmp_path / "reports.index",
        cwd=repo,
    )
    report_ref = "refs/wf/test/reports"
    git.update_ref(report_ref, report_commit, cwd=repo)
    evidence = producer.metadata.evidence
    assert evidence is not None
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "evidence": evidence.model_copy(
                        update={
                            "outputs_ref": report_ref,
                            "outputs_tree_oid": git.tree_oid(report_commit, cwd=repo),
                        }
                    )
                }
            )
        }
    )
    monkeypatch.setattr(
        git, "tree_blobs", lambda *_args, **_kwargs: (("120000", "0" * 40, "link"),)
    )
    with pytest.raises(InputsUnavailable, match="unsupported"):
        export_reference(git, repo, tmp_path, root, binding, producer)
    monkeypatch.undo()
    activation = tmp_path / "activation"
    activation.mkdir()
    first = json.loads(
        export_reference(
            git,
            repo,
            activation,
            root,
            binding,
            producer.model_copy(
                update={
                    "metadata": producer.metadata.model_copy(
                        update={"evidence": evidence}
                    )
                }
            ),
        )
    )
    destination = Path(first["index_path"]).parent
    (destination / "partial").write_text("stale", encoding="utf-8")
    rebuilt = json.loads(
        export_reference(
            git,
            repo,
            activation,
            root,
            binding,
            producer.model_copy(
                update={
                    "metadata": producer.metadata.model_copy(
                        update={"evidence": evidence}
                    )
                }
            ),
        )
    )
    assert not (Path(rebuilt["index_path"]).parent / "partial").exists()


def test_export_rejects_a_symlink_from_a_real_git_tree(
    fake_store, tmp_path: Path
) -> None:
    repo, git, root, producer, binding = _pinned_writer(fake_store, tmp_path)
    (repo / "report-link").symlink_to("source.txt")
    report_commit = git.snapshot_commit(
        message="symlink report",
        parents=(git.head_commit(cwd=repo),),
        index_path=tmp_path / "symlink.index",
        cwd=repo,
    )
    producer = _with_reports(producer, git, repo, "refs/wf/test/symlink", report_commit)

    with pytest.raises(InputsUnavailable, match="unsupported entry"):
        export_reference(git, repo, tmp_path, root, binding, producer)


def test_export_rejects_a_gitlink_from_a_real_git_tree(
    fake_store, tmp_path: Path
) -> None:
    repo, git, root, producer, binding = _pinned_writer(fake_store, tmp_path)
    add_submodule(repo, "vendored")
    report_commit = commit_all(repo, "gitlink report")
    producer = _with_reports(producer, git, repo, "refs/wf/test/gitlink", report_commit)

    with pytest.raises(InputsUnavailable, match="non-blob entry"):
        export_reference(git, repo, tmp_path, root, binding, producer)


def test_output_snapshot_export_requires_the_declared_tree(
    fake_store, tmp_path: Path
) -> None:
    repo, git, root, producer, _ = _pinned_writer(fake_store, tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "finding.md").write_text("output-only finding\n", encoding="utf-8")
    report_commit = git.commit_directory(
        ("finding.md",),
        root=reports,
        message="output snapshot",
        index_path=tmp_path / "outputs.index",
        cwd=repo,
    )
    report_ref = "refs/wf/test/output-only"
    git.update_ref(report_ref, report_commit, cwd=repo)
    tree = git.tree_oid(report_commit, cwd=repo)
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "node": "review",
                    "evidence": Evidence(
                        outputs_ref=report_ref,
                        outputs_tree_oid=tree,
                    ),
                }
            )
        }
    )
    binding = InputBinding(
        name="review_findings",
        producer_activation_id=producer.activation_id,
        artifact_ref=report_ref,
        digest=tree,
    )
    activation = tmp_path / "activation"
    activation.mkdir()

    index = json.loads(
        Path(
            json.loads(
                export_reference(git, repo, activation, root, binding, producer)
            )["index_path"]
        ).read_text(encoding="utf-8")
    )
    assert "diff_path" not in index
    assert Path(index["reports"][0]["path"]).read_text(encoding="utf-8") == (
        "output-only finding\n"
    )

    git.update_ref(report_ref, git.head_commit(cwd=repo), cwd=repo)
    with pytest.raises(InputsUnavailable, match="report tree does not resolve"):
        export_reference(git, repo, activation, root, binding, producer)


def test_repeat_export_reclaims_an_interrupted_stage(
    fake_store, tmp_path: Path
) -> None:
    repo, git, root, producer, binding = _pinned_writer(fake_store, tmp_path)
    activation = tmp_path / "activation"
    activation.mkdir()
    pointer = json.loads(
        export_reference(git, repo, activation, root, binding, producer)
    )
    destination = Path(pointer["index_path"]).parent
    stale = destination.parent / f".{destination.name}.{'0' * 32}.stage"
    stale.mkdir()
    (stale / "partial").write_text("interrupted", encoding="utf-8")
    unrelated = destination.parent / ".unrelated.00000000000000000000000000000000.stage"
    unrelated.mkdir()

    export_reference(git, repo, activation, root, binding, producer)

    assert not stale.exists()
    assert unrelated.is_dir()


def test_tree_entry_limit_reports_entries_not_bytes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    git = make_git(make_config(repo, tmp_path))
    reports = tmp_path / "reports"
    reports.mkdir()
    for name in ("one.txt", "two.txt"):
        (reports / name).write_text(name, encoding="utf-8")
    commit = git.commit_directory(
        ("one.txt", "two.txt"),
        root=reports,
        message="two reports",
        index_path=tmp_path / "reports.index",
        cwd=repo,
    )

    with pytest.raises(GitCommandError, match="exceeds 1 entries"):
        git.tree_blobs(
            git.tree_oid(commit, cwd=repo),
            cwd=repo,
            limit=1024,
            max_entries=1,
        )


def test_unusual_report_path_is_index_data_not_an_export_path(
    fake_store, tmp_path: Path
) -> None:
    repo, git, root, producer, binding = _pinned_writer(fake_store, tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    unusual = "dollar$; newline\nfinding.md"
    (reports / unusual).parent.mkdir(parents=True, exist_ok=True)
    (reports / unusual).write_text("finding", encoding="utf-8")
    commit = git.commit_directory(
        (unusual,),
        root=reports,
        message="reports",
        index_path=tmp_path / "reports.index",
        cwd=repo,
    )
    ref = "refs/wf/test/unusual"
    git.update_ref(ref, commit, cwd=repo)
    evidence = producer.metadata.evidence
    assert evidence is not None
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "evidence": evidence.model_copy(
                        update={
                            "outputs_ref": ref,
                            "outputs_tree_oid": git.tree_oid(commit, cwd=repo),
                        }
                    )
                }
            )
        }
    )
    activation = tmp_path / "activation"
    activation.mkdir()
    index = json.loads(
        Path(
            json.loads(
                export_reference(git, repo, activation, root, binding, producer)
            )["index_path"]
        ).read_text(encoding="utf-8")
    )
    assert index["reports"][0]["logical_path"] == unusual
    assert Path(index["reports"][0]["path"]).name == "report-000.txt"
