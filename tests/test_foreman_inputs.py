"""Focused C2a contracts for bound inputs and Q36 brief composition."""

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Final, cast

import pytest

from tests._bdio import IMPLEMENT, entry_request, load_definition, make_root
from tests._foreman import ForemanLab
from tests._foreman import entry_request as lab_entry_request
from tests._inspector import make_config, make_git, make_repo
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    ActivationRecord,
    Evidence,
    InputBinding,
    InstanceInput,
    Lifecycle,
    MintReason,
    RootRecord,
    SigningConfig,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.carriers import ArtifactIdentity
from workflow_interpreter.foreman.constants import FORCED_FIRST_REJECT
from workflow_interpreter.foreman.envelope import ComposedEnvelope, EnvelopeKind
from workflow_interpreter.foreman.inputs import (
    DefaultComposer,
    InputsUnavailable,
    Materialized,
    compose_resume_delta,
    materialize,
    select_bindings,
)
from workflow_interpreter.foreman.inspector import _task_builder
from workflow_interpreter.inspector import activation_ref, channels_for
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.schema.decisions import CoordinationLink
from workflow_interpreter.schema.models import Outcome, Region, RegionMode


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
            "id": "wf-earlier",
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
def test_compose_tells_the_crew_the_channel_protocol_for_its_own_node(
    fake_store: WorkflowStore, node: str, writes: bool, outcomes: tuple[str, ...]
) -> None:
    """cr-0zc: a real crew is told the §6 contract, or it fails closed.

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
def test_compose_tells_the_crew_what_its_own_node_must_do(
    fake_store: WorkflowStore, node: str
) -> None:
    """ADR 0002: instructions are pinned, hashed and enforced — and must arrive.

    The shipped graph is the participant here; the test authors none of the
    text it asserts on. A composer that stored instructions without rendering
    them would satisfy slices 1 and 2 and still tell the crew nothing.
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


def test_compose_carries_the_activation_facts_a_crew_cannot_derive(
    fake_store: WorkflowStore,
) -> None:
    """§6 gaps: the crew is told its node, round, graph and the checks that run."""
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


def test_leaf_contract_budget_and_mandatory_steer(fake_store: WorkflowStore) -> None:
    """Max legal instructions fit 16 KB; required context never silently drops."""
    from workflow_interpreter.foreman.constants import LEAF_EXECUTION_CONTRACT
    from workflow_interpreter.foreman.envelope import EnvelopeRefusal

    assert len(LEAF_EXECUTION_CONTRACT.encode()) <= 768
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    instructions = "Delegate to reviewers. " + "x" * (
        8192 - len("Delegate to reviewers. ")
    )
    document = root.definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(
                    update={"instructions": instructions, "context_budget_bytes": 16000}
                )
                if node.name == activation.metadata.node
                else node
                for node in root.definition.document.node
            )
        }
    )
    root = root.model_copy(
        update={"definition": root.definition.model_copy(update={"document": document})}
    )
    envelope = DefaultComposer().envelope(
        root,
        activation,
        (Materialized(text="original intent"),),
        instructions="保留 advice",
    )
    assert envelope.byte_count <= 16000
    assert instructions in envelope.text
    assert LEAF_EXECUTION_CONTRACT in envelope.text
    assert "保留 advice" in envelope.text
    with pytest.raises(EnvelopeRefusal):
        DefaultComposer().envelope(root, activation, (), instructions="x" * 16000)
    trimmed = DefaultComposer().envelope(
        root.model_copy(
            update={
                "index": root.index.model_copy(
                    update={
                        "sources": {
                            **root.index.sources,
                            "review_findings": root.index.sources[
                                "review_findings"
                            ].model_copy(update={"optional": True}),
                        }
                    }
                )
            }
        ),
        activation,
        (
            Materialized(text="original intent", name="task_brief"),
            Materialized(text="x" * 16000, name="review_findings"),
        ),
    )
    assert LEAF_EXECUTION_CONTRACT in trimmed.text
    assert "original intent" in trimmed.text
    assert any(
        item.name == "review_findings" and item.reason == "budget"
        for item in trimmed.omissions
    )
    small_document = document.model_copy(
        update={
            "node": tuple(
                node.model_copy(
                    update={"instructions": "Do the task.", "context_budget_bytes": 512}
                )
                if node.name == activation.metadata.node
                else node
                for node in document.node
            )
        }
    )
    with pytest.raises(EnvelopeRefusal):
        DefaultComposer().envelope(
            root.model_copy(
                update={
                    "definition": root.definition.model_copy(
                        update={"document": small_document}
                    )
                }
            ),
            activation,
            (),
        )


@pytest.mark.parametrize(
    "tamper", ["missing_binding", "source", "digest", "missing_ref"]
)
def test_optional_verify_feedback_never_hides_corrupt_bound_evidence(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer, tamper: str
) -> None:
    """Budget omission is allowed only after immutable diagnostics are verified."""
    from tests.test_foreman_fail_code_routing import (
        RED_IF_MARKER,
        RED_MARKER,
        _implement,
        _lab,
        _writes,
    )
    from tests.test_verify_feedback import feedback_graph
    from workflow_interpreter.foreman.inputs import bounded_materialize
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
    if tamper == "missing_binding":
        binding = binding.model_copy(update={"verify_failure": None})
    elif tamper == "source":
        binding = binding.model_copy(update={"producer_activation_id": target})
    elif tamper == "digest":
        binding = binding.model_copy(update={"digest": "0" * 64})
    else:
        lab.git.run(GitSubcommand.UPDATE_REF, "-d", binding.artifact_ref, cwd=lab.repo)
    with pytest.raises(InputsUnavailable):
        bounded_materialize(
            lab.git,
            lab.repo,
            root,
            binding,
            lab.store.reads.load_activation(source_id),
            limit=1,
        )


def _turn(
    store: WorkflowStore,
    root: RootRecord,
    turn_id: str,
    names: tuple[str, ...],
    *,
    source: str | None = None,
    sent: tuple[str, ...] | None = None,
    round_no: int = 1,
) -> ActivationRecord:
    """One turn of a resumed vendor thread, carrying the inputs it was given.

    `sent` is what its durable envelope record says the vendor actually got;
    by default every bound input, i.e. nothing was trimmed.
    """
    activation = store.mint_activation(root.root_id, entry_request()).activation
    bindings = tuple(
        InputBinding(
            name=name,
            producer_activation_id="instance",
            artifact_ref=f"refs/wf/{name}",
            digest=hashlib.sha256(name.encode()).hexdigest(),
        )
        for name in names
    )
    return activation.model_copy(
        update={
            "id": turn_id,
            "metadata": activation.metadata.model_copy(
                update={
                    "inputs": bindings,
                    "session_source_activation_id": source,
                    "round_no": round_no,
                    "envelope": {"included": list(names if sent is None else sent)},
                }
            ),
        }
    )


def test_resume_delta_drops_the_preamble_and_every_input_already_in_the_thread(
    fake_store: WorkflowStore,
) -> None:
    """A resumed turn appends only what is new to the thread it rejoins.

    The vendor already holds the protocol, the fact frame and every earlier
    turn's inputs; re-sending them is what the recomposed envelope did. The
    exclusion covers the whole CHAIN, so a third turn does not replay what the
    first one carried.
    """
    root = make_root(fake_store, load_definition())
    # `task_brief` reaches the thread on the FIRST turn only: the immediate
    # source alone cannot account for it, so a one-hop exclusion re-sends it.
    first = _turn(fake_store, root, "turn-1", ("task_brief",))
    second = _turn(
        fake_store, root, "turn-2", ("review_findings",), source=first.activation_id
    )
    third = _turn(
        fake_store,
        root,
        "turn-3",
        ("task_brief", "review_findings", "verify_failure"),
        source=second.activation_id,
    )
    node = root.index.nodes[third.metadata.node]
    assert node.instructions is not None

    delta = compose_resume_delta(
        root,
        third,
        second,
        {item.activation_id: item for item in (first, second, third)},
        (
            Materialized(text="the brief", name="task_brief", producer="instance"),
            Materialized(
                text="the findings", name="review_findings", producer="review"
            ),
            Materialized(text="the failure", name="verify_failure", producer="verify"),
        ),
    )

    assert node.instructions in delta.text
    assert "the failure" in delta.text
    assert "the brief" not in delta.text
    assert "the findings" not in delta.text
    assert "How this run is judged" not in delta.text
    assert delta.included == ("verify_failure",)


def _with_node(root: RootRecord, node: str, **update: object) -> RootRecord:
    """The root with one node's pinned body changed, as a graph could author it."""
    document = root.definition.document.model_copy(
        update={
            "node": tuple(
                item.model_copy(update=update) if item.name == node else item
                for item in root.definition.document.node
            )
        }
    )
    return root.model_copy(
        update={"definition": root.definition.model_copy(update={"document": document})}
    )


def test_resume_delta_resends_what_the_source_trimmed_and_owns_its_omissions(
    fake_store: WorkflowStore,
) -> None:
    """ "Already in the thread" is what the source's envelope SENT, not what it bound.

    `review_findings` was bound on turn 1 but trimmed from what it sent, so the
    thread never saw it and turn 2 must carry it. The delta applies the same
    budget: an optional input that does not fit is omitted and recorded as
    THIS turn's omission; nothing the delta did not drop is claimed as dropped.
    """
    base = make_root(fake_store, load_definition())
    first = _turn(
        fake_store,
        base,
        "turn-1",
        ("task_brief", "review_findings"),
        sent=("task_brief",),
    )
    root = _with_node(base, first.metadata.node, context_budget_bytes=4096)
    second = _turn(
        fake_store,
        root,
        "turn-2",
        ("task_brief", "review_findings"),
        source=first.activation_id,
    )
    chain = {item.activation_id: item for item in (first, second)}
    brief = Materialized(text="the brief", name="task_brief", producer="instance")

    def delta(findings: str) -> ComposedEnvelope:
        return compose_resume_delta(
            root,
            second,
            first,
            chain,
            (
                brief,
                Materialized(text=findings, name="review_findings", producer="review"),
            ),
        )

    resent = delta("the findings")
    trimmed = delta("x" * 8000)

    assert "the findings" in resent.text
    assert "the brief" not in resent.text
    assert resent.included == ("review_findings",)
    assert resent.omissions == ()
    assert trimmed.byte_count <= 4096
    assert trimmed.included == ()
    assert [(item.name, item.reason) for item in trimmed.omissions] == [
        ("review_findings", "budget")
    ]


def test_resumed_coordination_turn_carries_its_own_activation_facts(
    fake_store: WorkflowStore,
) -> None:
    """Every resumed turn re-states the per-activation facts the thread cannot hold.

    Turn 1's fact frame named turn 1: a round-3 decision stamped from it
    carries the wrong `producing_activation_id` and coordination refuses it.
    """
    root = make_root(fake_store, load_definition())
    root = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "coordination": CoordinationLink(
                        owner_id="owner",
                        slot="decision",
                        generation=0,
                        reservation_id="reservation",
                        ceiling=1,
                    )
                }
            )
        }
    )
    first = _turn(fake_store, root, "turn-1", ())
    third = _turn(
        fake_store, root, "turn-3", (), source=first.activation_id, round_no=3
    )

    delta = compose_resume_delta(
        root, third, first, {item.activation_id: item for item in (first, third)}, ()
    )

    assert f"producing_activation_id={third.activation_id}" in delta.text
    assert f"producing_root_id={root.root_id}" in delta.text
    assert first.activation_id not in delta.text
    assert "- round: 3" in delta.text
    assert "How this run is judged" not in delta.text


@pytest.mark.parametrize("appserver", [False, True])
def test_a_resumed_turn_records_the_envelope_it_actually_sent(
    tmp_path: Path, appserver: bool
) -> None:
    """The durable envelope of a resumed turn accounts for the delta, not the brief.

    The vendor receives `resume_brief`; recording the recomposed fresh envelope
    would make the record claim the crew was handed text it never saw. The
    frozen app-server resends the whole brief, so its record stays the
    pre-epic one: the fresh envelope, with no `kind`.
    """
    lab = ForemanLab(tmp_path, sandbox=SandboxMode.OFF)
    root = lab.instantiate()
    wiring = lab.wiring()
    node = root.index.nodes[IMPLEMENT]
    bindings = select_bindings(root.index, root, node, (), 1)
    source = wiring.store.mint_activation(
        root.root_id, lab_entry_request(inputs=bindings)
    ).activation
    wiring.store.close_activation(source.activation_id, Outcome.DONE)
    resumed = wiring.store.mint_activation(
        root.root_id,
        lab_entry_request(
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=source.activation_id,
            inputs=bindings,
        ),
    ).activation
    wiring.store._client._merge_metadata(
        resumed.activation_id,
        {"session_source_activation_id": source.activation_id}
        | (
            {
                "crew_profile": "codex-appserver",
                "binding_digest": None,
                "role": None,
                "family": None,
                "effort": None,
                "context_cap_tokens": None,
                "execution_policy": None,
                "policy_digest": None,
                "catalog_digest": None,
                "crew_version": None,
            }
            if appserver
            else {}
        ),
    )
    resumed = wiring.store.reads.load_activation(resumed.activation_id)
    paths = wiring.paths
    paths.ensure_activation_dir(resumed.activation_id)

    task = _task_builder(root, wiring, lab.git)(
        resumed,
        channels_for(
            paths.activation_dir(resumed.activation_id),
            paths.log(resumed.activation_id),
        ),
    )

    record = wiring.store.reads.load_activation(resumed.activation_id).metadata.envelope
    assert record is not None
    if appserver:
        assert task.resume_brief is None
        assert "kind" not in record
        assert record["sha256"] == hashlib.sha256(task.brief.encode()).hexdigest()
        return
    assert task.resume_brief is not None
    assert record["kind"] == EnvelopeKind.RESUME_DELTA.value
    assert record["byte_count"] == len(task.resume_brief.encode())
    assert record["sha256"] == hashlib.sha256(task.resume_brief.encode()).hexdigest()
    assert record["byte_count"] < len(task.brief.encode())
