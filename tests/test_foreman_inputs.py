"""Focused C2a contracts for bound inputs and Q36 brief composition."""

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Final, cast

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._supervisor import make_config, make_git, make_repo
from workflow_interpreter.bdio import (
    ActivationRecord,
    Evidence,
    InputBinding,
    InstanceInput,
    Lifecycle,
    RootRecord,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.carriers import ArtifactIdentity
from workflow_interpreter.foreman.constants import FORCED_FIRST_REJECT
from workflow_interpreter.foreman.inputs import (
    DefaultComposer,
    InputsUnavailable,
    Materialized,
    materialize,
    select_bindings,
)
from workflow_interpreter.schema.models import Outcome, Region, RegionMode
from workflow_interpreter.supervisor import activation_ref
from workflow_interpreter.supervisor.gitio import Git


class GitDouble:
    """Git boundary double that records only pinned-object reads."""

    _config = SimpleNamespace(repo_root=Path("."))

    def ref_target(self, ref: str, *, cwd: object) -> str | None:
        """Return the committed artifact named by the bound ref."""
        return "c" * 40

    def diff_text(self, base: str, head: str, *, cwd: object) -> str:
        """Return independent text for the pinned commit pair."""
        return f"{base}:{head}"

    def tree_entries(self, tree: str, *, cwd: object) -> tuple[str, ...]:
        """Return two pinned output objects."""
        return ("one", "two")

    def blob_text(self, oid: str, *, cwd: object) -> str:
        """Read one pinned output object."""
        return oid


def test_materialize_uses_instance_body_and_refuses_a_producer(
    fake_store: WorkflowStore,
) -> None:
    """F5 pins instance inputs to their stored body and digest."""
    root = make_root(fake_store, load_definition())
    root = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_inputs": (
                        InstanceInput(
                            name="task_brief",
                            sha256=hashlib.sha256(b"pinned").hexdigest(),
                            body="pinned",
                        ),
                    )
                }
            )
        }
    )
    binding = InputBinding(
        name="task_brief",
        producer_activation_id="instance",
        artifact_ref="wf-instance://task_brief",
        digest=hashlib.sha256(b"pinned").hexdigest(),
    )
    assert (
        materialize(cast(Git, GitDouble()), Path("."), root, binding, None).text
        == "pinned"
    )
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    with pytest.raises(InputsUnavailable):
        materialize(cast(Git, GitDouble()), Path("."), root, binding, activation)


@pytest.mark.parametrize(
    "binding",
    (
        InputBinding(
            name="task_brief",
            producer_activation_id="other",
            artifact_ref="wf-instance://task_brief",
            digest=hashlib.sha256(b"pinned").hexdigest(),
        ),
        InputBinding(
            name="task_brief",
            producer_activation_id="instance",
            artifact_ref="wf-instance://task_brief",
            digest=hashlib.sha256(b"other").hexdigest(),
        ),
        InputBinding(
            name="other",
            producer_activation_id="instance",
            artifact_ref="wf-instance://other",
            digest=hashlib.sha256(b"pinned").hexdigest(),
        ),
        InputBinding(
            name="task_brief",
            producer_activation_id="instance",
            artifact_ref="wf-instance://other",
            digest=hashlib.sha256(b"pinned").hexdigest(),
        ),
    ),
)
def test_materialize_refuses_every_unprovable_instance_binding(
    fake_store: WorkflowStore, binding: InputBinding
) -> None:
    """F5 accepts instance text only when every binding fact matches."""
    root = make_root(fake_store, load_definition())
    root = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_inputs": (
                        InstanceInput(
                            name="task_brief",
                            sha256=hashlib.sha256(b"pinned").hexdigest(),
                            body="pinned",
                        ),
                    )
                }
            )
        }
    )

    with pytest.raises(InputsUnavailable):
        materialize(cast(Git, GitDouble()), Path("."), root, binding, None)


def test_materialize_refuses_a_node_producer_without_evidence(
    fake_store: WorkflowStore,
) -> None:
    """F5 never reads a node input whose close has no durable evidence."""
    root = make_root(fake_store, load_definition())
    producer = fake_store.mint_activation(root.root_id, entry_request()).activation
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={"lifecycle": Lifecycle.CLOSED, "outcome": Outcome.DONE}
            )
        }
    )
    binding = InputBinding(
        name="diff_artifact",
        producer_activation_id=producer.activation_id,
        artifact_ref=activation_ref(root.root_id, producer.activation_id),
        digest="t" * 40,
    )

    with pytest.raises(InputsUnavailable):
        materialize(cast(Git, GitDouble()), Path("."), root, binding, producer)


@pytest.mark.parametrize(
    "artifact",
    (
        None,
        ArtifactIdentity(commit_oid="c" * 40, tree_oid="x" * 40),
        ArtifactIdentity(commit_oid="x" * 40, tree_oid="t" * 40),
    ),
)
def test_materialize_refuses_every_unprovable_writing_artifact(
    fake_store: WorkflowStore, artifact: ArtifactIdentity | None
) -> None:
    """F5 verifies a writing producer's artifact presence, tree, and ref."""
    root = make_root(fake_store, load_definition())
    producer = fake_store.mint_activation(root.root_id, entry_request()).activation
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={"evidence": Evidence(artifact=artifact)}
            )
        }
    )
    binding = InputBinding(
        name="diff_artifact",
        producer_activation_id=producer.activation_id,
        artifact_ref=activation_ref(root.root_id, producer.activation_id),
        digest="t" * 40,
    )

    with pytest.raises(InputsUnavailable):
        materialize(cast(Git, GitDouble()), Path("."), root, binding, producer)


def test_select_bindings_and_materialize_recover_pinned_node_outputs(
    fake_store: WorkflowStore,
) -> None:
    """F5 selects the latest completed producer and reads its output tree."""
    root = make_root(fake_store, load_definition())
    root = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_inputs": (
                        InstanceInput(
                            name="task_brief",
                            sha256=hashlib.sha256(b"brief").hexdigest(),
                            body="brief",
                        ),
                    )
                }
            )
        }
    )
    producer = fake_store.mint_activation(root.root_id, entry_request()).activation
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "node": "implement",
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="c" * 40, tree_oid="t" * 40
                        )
                    ),
                }
            )
        }
    )
    bindings = select_bindings(
        root.index,
        root,
        root.index.nodes["review"],
        (producer,),
        producer.metadata.round_no,
    )
    assert bindings == (
        InputBinding(
            name="task_brief",
            producer_activation_id="instance",
            artifact_ref="wf-instance://task_brief",
            digest=hashlib.sha256(b"brief").hexdigest(),
        ),
        InputBinding(
            name="diff_artifact",
            producer_activation_id=producer.activation_id,
            artifact_ref=activation_ref(root.root_id, producer.activation_id),
            digest="t" * 40,
        ),
    )
    assert materialize(
        cast(Git, GitDouble()), Path("."), root, bindings[1], producer
    ).text == (f"{producer.metadata.intended_base_commit}:{'c' * 40}")

    document = root.definition.document.model_copy(
        update={
            "node": tuple(
                item.model_copy(update={"writes": False})
                if item.name == "implement"
                else item
                for item in root.definition.document.node
            )
        }
    )
    nonwriting_root = root.model_copy(
        update={"definition": root.definition.model_copy(update={"document": document})}
    )
    outputs_producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "evidence": Evidence(
                        outputs_ref="refs/wf/outputs/implement",
                        outputs_tree_oid="t" * 40,
                    )
                }
            )
        }
    )
    outputs_binding = InputBinding(
        name="diff_artifact",
        producer_activation_id=producer.activation_id,
        artifact_ref="refs/wf/outputs/implement",
        digest="t" * 40,
    )
    assert (
        materialize(
            cast(Git, GitDouble()),
            Path("."),
            nonwriting_root,
            outputs_binding,
            outputs_producer,
        ).text
        == f"--- one ---\n{'t' * 40}:one\n--- two ---\n{'t' * 40}:two"
    )
    for field, value in (
        ("producer_activation_id", "other"),
        ("artifact_ref", "refs/wf/outputs/other"),
        ("digest", "x" * 40),
    ):
        with pytest.raises(InputsUnavailable):
            materialize(
                cast(Git, GitDouble()),
                Path("."),
                nonwriting_root,
                outputs_binding.model_copy(update={field: value}),
                outputs_producer,
            )


def test_select_bindings_requires_a_completed_non_optional_producer(
    fake_store: WorkflowStore,
) -> None:
    """F5 does not bind an absent or incomplete required producer."""
    root = make_root(fake_store, load_definition())
    with pytest.raises(InputsUnavailable):
        select_bindings(
            root.index,
            root,
            root.index.nodes["review"],
            (),
            1,
        )


def test_select_bindings_skips_optional_instance_and_node_sources(
    fake_store: WorkflowStore,
) -> None:
    """Optional sources do not turn an otherwise usable task into a refusal."""
    root = make_root(fake_store, load_definition())
    index = root.index.model_copy(
        update={
            "sources": {
                **root.index.sources,
                "task_brief": root.index.sources["task_brief"].model_copy(
                    update={"optional": True}
                ),
            }
        }
    )

    assert select_bindings(index, root, index.nodes["implement"], (), 1) == ()


def test_materialize_reads_real_pinned_output_tree_paths_as_blobs(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A non-writing producer materializes real tree entries, never path names."""
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path)
    git = make_git(config)
    outputs = tmp_path / "outputs"
    (outputs / "first.md").parent.mkdir(parents=True)
    (outputs / "first.md").write_text("first finding\n", encoding="utf-8")
    (outputs / "second.md").write_text("second finding\n", encoding="utf-8")
    commit = git.commit_directory(
        ("first.md", "second.md"),
        root=outputs,
        message="pinned findings",
        index_path=tmp_path / "outputs.index",
        cwd=repo,
    )
    tree_oid = git.tree_oid(commit, cwd=repo)
    root = make_root(fake_store, load_definition())
    producer = fake_store.mint_activation(root.root_id, entry_request()).activation
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "node": "review",
                    "evidence": Evidence(
                        outputs_ref="wf-outputs://review",
                        outputs_tree_oid=tree_oid,
                    ),
                }
            )
        }
    )
    binding = InputBinding(
        name="diff_artifact",
        producer_activation_id=producer.activation_id,
        artifact_ref="wf-outputs://review",
        digest=tree_oid,
    )

    materialized = materialize(git, repo, root, binding, producer)

    assert materialized.text == (
        "--- first.md ---\nfirst finding\n\n--- second.md ---\nsecond finding\n"
    )


def test_select_bindings_prefers_the_current_round_and_refuses_incomplete_producers(
    fake_store: WorkflowStore,
) -> None:
    """F5 binds the current completed producer, never an unproved fallback."""
    root = make_root(fake_store, load_definition())
    root = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_inputs": (
                        InstanceInput(
                            name="task_brief",
                            sha256=hashlib.sha256(b"brief").hexdigest(),
                            body="brief",
                        ),
                    )
                }
            )
        }
    )
    current = fake_store.mint_activation(root.root_id, entry_request()).activation
    current = current.model_copy(
        update={
            "metadata": current.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="c" * 40, tree_oid="t" * 40
                        )
                    ),
                }
            )
        }
    )
    later = fake_store.mint_activation(root.root_id, entry_request()).activation
    later = later.model_copy(
        update={
            "metadata": later.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "round_no": current.metadata.round_no + 1,
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="d" * 40, tree_oid="u" * 40
                        )
                    ),
                }
            )
        }
    )
    bindings = select_bindings(
        root.index,
        root,
        root.index.nodes["review"],
        (current, later),
        current.metadata.round_no,
    )

    assert bindings[1].producer_activation_id == current.activation_id


def test_select_bindings_does_not_bind_a_later_sequence_from_an_earlier_round(
    fake_store: WorkflowStore,
) -> None:
    """F5 selects only the requested round before using sequence as a tiebreaker."""
    root = make_root(fake_store, load_definition())
    root = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_inputs": (
                        InstanceInput(
                            name="task_brief",
                            sha256=hashlib.sha256(b"brief").hexdigest(),
                            body="brief",
                        ),
                    )
                }
            )
        }
    )
    current = fake_store.mint_activation(root.root_id, entry_request()).activation
    current = current.model_copy(
        update={
            "metadata": current.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "round_no": 2,
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="c" * 40, tree_oid="t" * 40
                        )
                    ),
                }
            )
        }
    )
    earlier = current.model_copy(
        update={
            "bead": current.bead.model_copy(update={"id": "wf-earlier"}),
            "metadata": current.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "round_no": 1,
                    "seq": int(current.metadata.seq) + 1,
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="d" * 40, tree_oid="u" * 40
                        )
                    ),
                }
            ),
        }
    )

    bindings = select_bindings(
        root.index,
        root,
        root.index.nodes["review"],
        (current, earlier),
        2,
    )

    assert bindings[1].producer_activation_id == current.activation_id


@pytest.mark.parametrize(
    ("evidence", "writes", "message"),
    (
        pytest.param(None, True, "no evidence", id="evidence"),
        pytest.param(Evidence(), True, "no artifact", id="artifact"),
        pytest.param(
            Evidence(outputs_ref="refs/wf/outputs/implement"),
            False,
            "no pinned outputs",
            id="outputs",
        ),
    ),
)
def test_select_bindings_refuses_a_selected_producer_without_its_proof(
    fake_store: WorkflowStore,
    evidence: Evidence | None,
    writes: bool,
    message: str,
) -> None:
    """F5 refuses a selected producer whose durable proof is incomplete."""
    root = make_root(fake_store, load_definition())
    root = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_inputs": (
                        InstanceInput(
                            name="task_brief",
                            sha256=hashlib.sha256(b"brief").hexdigest(),
                            body="brief",
                        ),
                    )
                }
            )
        }
    )
    if not writes:
        document = root.definition.document.model_copy(
            update={
                "node": tuple(
                    item.model_copy(update={"writes": False})
                    if item.name == "implement"
                    else item
                    for item in root.definition.document.node
                )
            }
        )
        root = root.model_copy(
            update={
                "definition": root.definition.model_copy(update={"document": document})
            }
        )
    producer = fake_store.mint_activation(root.root_id, entry_request()).activation
    producer = producer.model_copy(
        update={
            "metadata": producer.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "evidence": evidence,
                }
            )
        }
    )

    with pytest.raises(InputsUnavailable, match=message):
        select_bindings(
            root.index,
            root,
            root.index.nodes["review"],
            (producer,),
            producer.metadata.round_no,
        )


@pytest.mark.parametrize(
    ("allow", "flag", "round_no", "node", "contains"),
    [
        (True, True, 1, "review", True),
        (False, True, 1, "review", False),
        (True, False, 1, "review", False),
        (True, True, 2, "review", False),
        (True, True, 1, "implement", False),
    ],
)
def test_default_composer_pins_every_forced_reject_clause(
    fake_store: WorkflowStore,
    allow: bool,
    flag: bool,
    round_no: int,
    node: str,
    contains: bool,
) -> None:
    """Q36 fires only for the four-way pinned first-review guard."""
    root = make_root(fake_store, load_definition())
    definition = root.definition.model_copy(
        update={
            "document": root.definition.document.model_copy(
                update={
                    "instance": root.definition.document.instance.model_copy(
                        update={"test_force_first_reject": flag}
                    )
                }
            )
        }
    )
    root = root.model_copy(
        update={
            "definition": definition,
            "metadata": root.metadata.model_copy(update={"allow_test_flags": allow}),
        }
    )
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"node": node, "round_no": round_no}
            )
        }
    )
    brief = DefaultComposer().compose(root, activation, (Materialized(text="body"),))
    assert (FORCED_FIRST_REJECT in brief) is contains


@pytest.mark.parametrize(
    ("node", "writes", "outcomes"),
    (
        ("implement", True, ("done", "no_diff", "fail_plan")),
        ("review", False, ("accept", "reject")),
    ),
)
def test_compose_tells_the_runner_the_channel_protocol_for_its_own_node(
    fake_store: WorkflowStore, node: str, writes: bool, outcomes: tuple[str, ...]
) -> None:
    """cr-0zc: a real runner is told the §6 contract, or it fails closed.

    Found by the live DRILL-27 run, and structurally invisible to the lab: the
    `ShellProfile` double always wrote `$WF_OUTCOME_FILE` because the TEST
    authored the script that wrote it. A real `claude` did the task, passed
    verify, then exited 0 having written neither channel and committed nothing
    — because the composed brief was the task text and nothing else.
    """
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={"metadata": activation.metadata.model_copy(update={"node": node})}
    )

    brief = DefaultComposer().compose(root, activation, (Materialized(text="body"),))

    assert "$WF_OUTCOME_FILE" in brief
    assert "$WF_EFFECTS_FILE" in brief
    assert "$WF_ARTIFACT_DIR" in brief
    # The node's OWN declared outcomes, not a fixed vocabulary: a marker
    # carrying an outcome the node does not declare grades `fail_code` (§6).
    for outcome in outcomes:
        assert outcome in brief
    # A non-writing node must be told so; §7.5 grades its repo writes as
    # undeclared effects regardless of what it intended.
    assert ("commit" in brief) is writes
    assert brief.endswith("body")


@pytest.mark.parametrize("node", ("implement", "review"))
def test_compose_tells_the_runner_what_its_own_node_must_do(
    fake_store: WorkflowStore, node: str
) -> None:
    """ADR 0002: instructions are pinned, hashed and enforced — and must arrive.

    The shipped graph is the participant here; the test authors none of the
    text it asserts on. A composer that stored instructions without rendering
    them would satisfy slices 1 and 2 and still tell the runner nothing.
    """
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={"metadata": activation.metadata.model_copy(update={"node": node})}
    )
    instructions = root.index.nodes[node].instructions
    assert instructions, (
        "fixture must carry instructions for this test to mean anything"
    )

    brief = DefaultComposer().compose(root, activation, (Materialized(text="body"),))

    assert instructions.strip() in brief


def test_compose_states_that_declared_facts_beat_instructions(
    fake_store: WorkflowStore,
) -> None:
    """Prose can contradict the pinned graph; the graph is what grades the run."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation

    brief = DefaultComposer().compose(root, activation, (Materialized(text="body"),))

    assert "declared facts" in brief.lower()


def test_compose_carries_the_activation_facts_a_runner_cannot_derive(
    fake_store: WorkflowStore,
) -> None:
    """§6 gaps: the runner is told its node, round, graph and the checks that run."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    node = root.index.nodes[activation.metadata.node]

    brief = DefaultComposer().compose(root, activation, (Materialized(text="body"),))

    assert activation.metadata.node in brief
    assert root.definition.document.graph.id in brief
    assert str(activation.metadata.round_no) in brief
    for check in node.verify or ():
        assert check.cmd in brief


def test_compose_labels_each_input_with_its_name_and_producer(
    fake_store: WorkflowStore,
) -> None:
    """Unlabeled concatenation makes two inputs one wall of text (§6)."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation

    brief = DefaultComposer().compose(
        root,
        activation,
        (
            Materialized(text="the brief", name="task_brief", producer="instance"),
            Materialized(
                text="the findings", name="review_findings", producer="review"
            ),
        ),
    )

    assert "task_brief" in brief
    assert "review_findings" in brief
    assert brief.index("task_brief") < brief.index("review_findings")
    assert "the brief" in brief and "the findings" in brief


REVIEW_REGION: Final[str] = "review-only"
"""A second region for `review`, so `implement` produces across a boundary."""


def _with_task_brief(root: RootRecord) -> RootRecord:
    """Give an instance the one pinned instance input every binding test needs."""
    return root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_inputs": (
                        InstanceInput(
                            name="task_brief",
                            sha256=hashlib.sha256(b"brief").hexdigest(),
                            body="brief",
                        ),
                    )
                }
            )
        }
    )


def _split_regions(root: RootRecord) -> RootRecord:
    """Move `review` into its own region, leaving `implement` where it is."""
    document = root.definition.document
    document = document.model_copy(
        update={
            "region": (
                *document.region,
                Region(
                    name=REVIEW_REGION,
                    mode=RegionMode.ACYCLIC,
                    entry_node="review",
                ),
            ),
            "node": tuple(
                item.model_copy(update={"region": REVIEW_REGION})
                if item.name == "review"
                else item
                for item in document.node
            ),
        }
    )
    return _with_task_brief(
        root.model_copy(
            update={
                "definition": root.definition.model_copy(update={"document": document})
            }
        )
    )


def _closed_implement(
    fake_store: WorkflowStore,
    root: RootRecord,
    *,
    round_no: int,
    seq_delta: int = 0,
    tree_oid: str = "t" * 40,
) -> ActivationRecord:
    """A completed `implement` activation with a proved artifact."""
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    return activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "round_no": round_no,
                    "seq": int(activation.metadata.seq) + seq_delta,
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="c" * 40, tree_oid=tree_oid
                        )
                    ),
                }
            )
        }
    )


def test_select_bindings_takes_the_latest_closed_producer_across_regions(
    fake_store: WorkflowStore,
) -> None:
    """D1: rounds are per-region counters, so they cannot order a foreign producer."""
    root = _split_regions(make_root(fake_store, load_definition()))
    older = _closed_implement(fake_store, root, round_no=3)
    latest = _closed_implement(
        fake_store, root, round_no=1, seq_delta=1, tree_oid="u" * 40
    )

    bindings = select_bindings(
        root.index, root, root.index.nodes["review"], (older, latest), 3
    )

    assert bindings[1] == InputBinding(
        name="diff_artifact",
        producer_activation_id=latest.activation_id,
        artifact_ref=activation_ref(root.root_id, latest.activation_id),
        digest="u" * 40,
    )


def test_select_bindings_falls_back_to_the_latest_round_in_the_same_region(
    fake_store: WorkflowStore,
) -> None:
    """Same-region binding is unchanged: current round first, else most recent."""
    root = _with_task_brief(make_root(fake_store, load_definition()))
    first = _closed_implement(fake_store, root, round_no=1)
    second = _closed_implement(
        fake_store, root, round_no=2, seq_delta=1, tree_oid="u" * 40
    )

    assert (
        select_bindings(root.index, root, root.index.nodes["review"], (first,), 2)[
            1
        ].producer_activation_id
        == first.activation_id
    )
    assert (
        select_bindings(
            root.index, root, root.index.nodes["review"], (first, second), 2
        )[1].producer_activation_id
        == second.activation_id
    )


def test_select_bindings_binds_an_optional_cross_region_producer_once_closed(
    fake_store: WorkflowStore,
) -> None:
    """An optional foreign input binds nothing while absent, its producer once closed."""
    root = _split_regions(make_root(fake_store, load_definition()))
    review = fake_store.mint_activation(root.root_id, entry_request()).activation
    review = review.model_copy(
        update={
            "metadata": review.metadata.model_copy(
                update={
                    "node": "review",
                    "region": REVIEW_REGION,
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.ACCEPT,
                    "evidence": Evidence(
                        outputs_ref="refs/wf/outputs/review",
                        outputs_tree_oid="o" * 40,
                    ),
                }
            )
        }
    )

    absent = select_bindings(root.index, root, root.index.nodes["implement"], (), 1)
    present = select_bindings(
        root.index, root, root.index.nodes["implement"], (review,), 1
    )

    assert tuple(binding.name for binding in absent) == ("task_brief",)
    assert tuple(binding.name for binding in present) == (
        "task_brief",
        "review_findings",
    )
    assert present[1].producer_activation_id == review.activation_id


def test_select_bindings_refuses_a_required_absent_cross_region_producer(
    fake_store: WorkflowStore,
) -> None:
    """A required foreign input with no closed producer is still unavailable."""
    root = _split_regions(make_root(fake_store, load_definition()))
    open_producer = fake_store.mint_activation(root.root_id, entry_request()).activation

    with pytest.raises(InputsUnavailable, match="implement"):
        select_bindings(
            root.index, root, root.index.nodes["review"], (open_producer,), 1
        )
