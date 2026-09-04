"""Bound-input materialization and deterministic task-brief composition."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ActivationRecord, InputBinding, RootRecord
from workflow_interpreter.bdio.mint import FIRST_ROUND
from workflow_interpreter.foreman.constants import (
    FACT_FRAME,
    FACT_FRAME_NO_PATHS,
    FORCED_FIRST_REJECT,
    INPUT_LABEL,
    RUNNER_PROTOCOL,
    RUNNER_PROTOCOL_NO_WRITE_STEP,
    RUNNER_PROTOCOL_WRITE_STEP,
)
from workflow_interpreter.schema.graph_index import GraphIndex, producer_node
from workflow_interpreter.schema.models import Node, Outcome
from workflow_interpreter.supervisor import activation_ref
from workflow_interpreter.supervisor.gitio import Git


class InputsUnavailable(ValueError):
    """A bound input cannot be proved against its pinned producer state."""


class Materialized(BaseModel):
    """Immutable text recovered from one previously bound input.

    Carries its own provenance because the composer renders several of these
    into one brief: without a name and producer they concatenate into a
    single unattributed wall of text (ADR 0002).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    name: str = ""
    producer: str = ""


def select_bindings(
    index: GraphIndex,
    root: RootRecord,
    node: Node,
    activations: tuple[ActivationRecord, ...],
    round_no: int,
) -> tuple[InputBinding, ...]:
    """Bind each declared source to the latest proved producer output."""
    bindings: list[InputBinding] = []
    for name in node.inputs or ():
        source = index.sources[name]
        producer_node_name = producer_node(source)
        if producer_node_name is None:
            instance = next(
                (item for item in root.metadata.instance_inputs if item.name == name),
                None,
            )
            if instance is None:
                if source.optional:
                    continue
                raise InputsUnavailable(
                    f"required instance input {name!r} is unavailable"
                )
            bindings.append(
                InputBinding(
                    name=name,
                    producer_activation_id="instance",
                    artifact_ref=f"wf-instance://{name}",
                    digest=instance.sha256,
                )
            )
            continue
        # `round_no` counts entries into ONE region (§10.1), so it orders a
        # producer only when producer and consumer share that counter. Across a
        # boundary the latest CLOSED activation is the whole candidate set and
        # `seq` is the only ordering left (spec §2 "Input binding").
        same_region = index.nodes[producer_node_name].region == node.region
        candidates = tuple(
            activation
            for activation in activations
            if activation.metadata.is_completed
            and activation.metadata.node == producer_node_name
            and (not same_region or activation.metadata.region == node.region)
        )
        current_round = (
            tuple(
                activation
                for activation in candidates
                if activation.metadata.round_no == round_no
            )
            if same_region
            else ()
        )
        producer = max(
            current_round or candidates,
            key=lambda activation: int(activation.metadata.seq),
            default=None,
        )
        if producer is None:
            if source.optional:
                continue
            raise InputsUnavailable(
                f"required producer {producer_node_name!r} is unavailable"
            )
        evidence = producer.metadata.evidence
        if evidence is None:
            raise InputsUnavailable("completed input producer has no evidence")
        if index.nodes[producer_node_name].writes:
            artifact = evidence.artifact
            if artifact is None:
                raise InputsUnavailable("writing input producer has no artifact")
            bindings.append(
                InputBinding(
                    name=name,
                    producer_activation_id=producer.activation_id,
                    artifact_ref=activation_ref(root.root_id, producer.activation_id),
                    digest=artifact.tree_oid,
                )
            )
            continue
        if evidence.outputs_ref is None or evidence.outputs_tree_oid is None:
            raise InputsUnavailable("non-writing input producer has no pinned outputs")
        bindings.append(
            InputBinding(
                name=name,
                producer_activation_id=producer.activation_id,
                artifact_ref=evidence.outputs_ref,
                digest=evidence.outputs_tree_oid,
            )
        )
    return tuple(bindings)


def materialize(
    git: Git,
    repo_root: Path,
    root: RootRecord,
    binding: InputBinding,
    producer: ActivationRecord | None,
) -> Materialized:
    """Read one bound input exclusively from the pinned git objects."""
    if producer is None:
        if (
            binding.producer_activation_id != "instance"
            or binding.artifact_ref != f"wf-instance://{binding.name}"
        ):
            raise InputsUnavailable("instance input does not match its binding")
        instance = next(
            (
                item
                for item in root.metadata.instance_inputs
                if item.name == binding.name and item.sha256 == binding.digest
            ),
            None,
        )
        if instance is None:
            raise InputsUnavailable("instance input does not match its binding")
        return Materialized(text=instance.body, name=binding.name, producer="instance")
    if producer.activation_id != binding.producer_activation_id:
        raise InputsUnavailable("input producer does not match its binding")
    evidence = producer.metadata.evidence
    node = root.index.nodes[producer.metadata.node]
    if evidence is None:
        raise InputsUnavailable("input producer has no evidence")
    if node.writes:
        artifact = evidence.artifact
        if (
            artifact is None
            or artifact.tree_oid != binding.digest
            or git.ref_target(binding.artifact_ref, cwd=repo_root)
            != artifact.commit_oid
        ):
            raise InputsUnavailable("writing input does not match its artifact")
        base = (
            producer.metadata.pre_attempt_commit
            or producer.metadata.intended_base_commit
        )
        return Materialized(
            text=git.diff_text(base, artifact.commit_oid, cwd=repo_root),
            name=binding.name,
            producer=producer.metadata.node,
        )
    if (
        evidence.outputs_ref != binding.artifact_ref
        or evidence.outputs_tree_oid != binding.digest
    ):
        raise InputsUnavailable("output tree does not match its binding")
    return Materialized(
        text="\n".join(
            f"--- {path} ---\n{git.blob_text(f'{binding.digest}:{path}', cwd=repo_root)}"
            for path in git.tree_entries(binding.digest, cwd=repo_root)
        ),
        name=binding.name,
        producer=producer.metadata.node,
    )


def _runner_protocol(node: Node) -> str:
    """Render the §6 channel contract for one node's own permissions."""
    return RUNNER_PROTOCOL.format(
        write_step=(
            RUNNER_PROTOCOL_WRITE_STEP if node.writes else RUNNER_PROTOCOL_NO_WRITE_STEP
        ),
        outcomes=", ".join(item.value for item in node.outcomes or ()),
    )


def _fact_frame(root: RootRecord, activation: ActivationRecord, node: Node) -> str:
    """Render the pinned facts that decide how this activation is graded."""
    graph = root.definition.document.graph
    return FACT_FRAME.format(
        node=node.name,
        graph_id=graph.id,
        graph_version=graph.version,
        round_no=activation.metadata.round_no,
        writes="yes" if node.writes else "no",
        allowed_paths=", ".join(node.allowed_paths or ()) or FACT_FRAME_NO_PATHS,
        verify=", ".join(check.cmd for check in node.verify or ())
        or FACT_FRAME_NO_PATHS,
    )


def _labelled(item: Materialized) -> str:
    """Attribute one input to its source, or pass it through when unattributed."""
    if not item.name:
        return item.text
    return "\n".join(
        (
            INPUT_LABEL.format(name=item.name, producer=item.producer or "unknown"),
            item.text,
        )
    )


class DefaultComposer:
    """Join materialized inputs and add the narrowly opted-in test clause."""

    def compose(
        self,
        root: RootRecord,
        activation: ActivationRecord,
        inputs: tuple[Materialized, ...],
    ) -> str:
        """Compose the profile brief from immutable inputs and pinned flags."""
        node = root.index.nodes[activation.metadata.node]
        # One blank line between sections: the runner reads a document, not a
        # run-on. Each part is stripped so section spacing is the joiner's
        # job alone, whatever trailing newlines a template or input carries.
        brief = "\n\n".join(
            part.strip()
            for part in (
                _runner_protocol(node),
                _fact_frame(root, activation, node),
                node.instructions or "",
                *(_labelled(item) for item in inputs),
            )
            if part.strip()
        )
        forced = (
            root.metadata.allow_test_flags
            and root.definition.document.instance.test_force_first_reject
            and Outcome.REJECT in (node.outcomes or ())
            and activation.metadata.round_no == FIRST_ROUND
        )
        return "\n".join(
            (*filter(None, (brief, FORCED_FIRST_REJECT if forced else "")),)
        )
