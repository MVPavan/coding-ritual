"""Bound-input materialization and deterministic task-brief composition."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ActivationRecord, InputBinding, RootRecord
from workflow_interpreter.bdio.mint import FIRST_ROUND
from workflow_interpreter.contracts.sessions import SessionMode
from workflow_interpreter.foreman.constants import (
    CREW_PROTOCOL,
    CREW_PROTOCOL_NO_WRITE_STEP,
    CREW_PROTOCOL_WRITE_STEP,
    EVIDENCE_REFERENCE_INSTRUCTIONS,
    FACT_FRAME,
    FACT_FRAME_NO_PATHS,
    FORCED_FIRST_REJECT,
    INPUT_LABEL,
    LEAF_EXECUTION_CONTRACT,
    MSG_INPUT_SOURCE_UNDECLARED,
    RESUME_FACT_FRAME,
    RESUMED_NON_WRITER_REVIEW_DELTA,
)
from workflow_interpreter.foreman.envelope import (
    ComposedEnvelope,
    EnvelopeKind,
    EnvelopeSection,
    InputOmission,
    InputsUnavailable,
    compose_envelope,
)
from workflow_interpreter.foreman.execution import resolved_static_node
from workflow_interpreter.inspector import activation_ref
from workflow_interpreter.inspector.gitcmd import GitOutputTooLarge, GitSubcommand
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.schema.graph_index import (
    GraphIndex,
    producer_engine,
    producer_node,
)
from workflow_interpreter.schema.models import (
    ArtifactInputMode,
    EngineProducer,
    Node,
    Outcome,
)

__all__ = [
    "DefaultComposer",
    "InputsUnavailable",
    "Materialized",
    "ResumeDelta",
    "bounded_materialize",
    "compose_resume_delta",
    "materialize",
    "select_bindings",
]


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
    omission: InputOmission | None = None


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
        if producer_engine(source) is not None:
            # Bound only by the causal routing seam, never as an instance input.
            continue
        producer_node_name = producer_node(source)
        if producer_node_name is None:
            instance = next(
                (item for item in root.metadata.instance_inputs if item.name == name),
                None,
            )
            if instance is None:
                if source.optional and name not in (
                    root.metadata.essential_inputs or ()
                ):
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
        # The producer's EFFECTIVE `writes`: it ran under the root's
        # resolution, so binding it under the raw pinned value looks for an
        # artifact that was never produced (cr-7h8 review).
        if resolved_static_node(root, producer_node_name).writes:
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
    *,
    limit: int | None = None,
) -> Materialized:
    """Read one bound input exclusively from the pinned git objects."""
    source = root.index.sources.get(binding.name)
    if source is None:
        raise InputsUnavailable(MSG_INPUT_SOURCE_UNDECLARED)
    engine = producer_engine(source)
    if binding.ledger_render is not None or engine is EngineProducer.LEDGER_RENDER:
        from workflow_interpreter.foreman.ledger_render import (
            read_render,
            render_envelope_text,
        )

        return Materialized(
            text=render_envelope_text(read_render(git, repo_root, binding)),
            name=binding.name,
            producer=EngineProducer.LEDGER_RENDER.value,
        )
    if binding.verify_failure is not None or engine is not None:
        from workflow_interpreter.foreman.verify_feedback import read_payload

        body = read_payload(git, repo_root, root, binding, producer)
        return Materialized(
            text=body.decode(),
            name=binding.name,
            producer=EngineProducer.VERIFY_FAILURE.value,
        )
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
    node = resolved_static_node(root, producer.metadata.node)
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
            text=(
                git.diff_text(base, artifact.commit_oid, cwd=repo_root)
                if limit is None
                else git.bounded_text(
                    GitSubcommand.DIFF,
                    "--no-ext-diff",
                    "--no-textconv",
                    base,
                    artifact.commit_oid,
                    cwd=repo_root,
                    limit=limit,
                )
            ),
            name=binding.name,
            producer=producer.metadata.node,
        )
    if (
        evidence.outputs_ref != binding.artifact_ref
        or evidence.outputs_tree_oid != binding.digest
    ):
        raise InputsUnavailable("output tree does not match its binding")
    paths = (
        git.tree_entries(binding.digest, cwd=repo_root)
        if limit is None
        else tuple(
            filter(
                None,
                git.bounded_text(
                    GitSubcommand.LS_TREE,
                    "-r",
                    "-z",
                    "--name-only",
                    binding.digest,
                    cwd=repo_root,
                    limit=limit,
                ).split("\0"),
            )
        )
    )
    parts: list[str] = []
    remaining = limit
    for path in paths:
        label = f"--- {path} ---\n"
        if remaining is not None:
            remaining -= len(label.encode()) + (1 if parts else 0)
            if remaining < 0:
                raise GitOutputTooLarge(limit or 0)
        text = (
            git.blob_text(f"{binding.digest}:{path}", cwd=repo_root)
            if remaining is None
            else git.bounded_text(
                GitSubcommand.CAT_FILE,
                "blob",
                f"{binding.digest}:{path}",
                cwd=repo_root,
                limit=remaining,
            )
        )
        parts.append(label + text)
        if remaining is not None:
            remaining -= len(text.encode())
    return Materialized(
        text="\n".join(parts), name=binding.name, producer=producer.metadata.node
    )


def bounded_materialize(
    git: Git,
    repo_root: Path,
    root: RootRecord,
    binding: InputBinding,
    producer: ActivationRecord | None,
    *,
    limit: int,
) -> Materialized:
    """Overflowing optional objects stay by reference; essential ones refuse."""
    try:
        return materialize(git, repo_root, root, binding, producer, limit=limit)
    except GitOutputTooLarge:
        source = root.index.sources[binding.name]
        if source.optional and binding.name not in (
            root.metadata.essential_inputs or ()
        ):
            return Materialized(
                text="",
                name=binding.name,
                producer=source.producer,
                omission=InputOmission(
                    name=binding.name,
                    reason="budget",
                    reference=binding.artifact_ref,
                    digest=binding.digest,
                    measured_bytes=limit + 1,
                    exact=False,
                ),
            )
        from workflow_interpreter.foreman.envelope import EnvelopeRefusal

        raise EnvelopeRefusal(limit + 1, limit, exact=False) from None


def _crew_protocol(node: Node) -> str:
    """Render the §6 channel contract for one node's own permissions."""
    return CREW_PROTOCOL.format(
        write_step=(
            CREW_PROTOCOL_WRITE_STEP if node.writes else CREW_PROTOCOL_NO_WRITE_STEP
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


def _execution_identity(root: RootRecord, activation: ActivationRecord) -> str:
    """The ids a coordinated decision must stamp, or nothing outside one."""
    if root.metadata.coordination is None:
        return ""
    return (
        f"Execution identity: producing_root_id={root.root_id}; "
        f"producing_activation_id={activation.activation_id}"
    )


def _forced_first_reject(
    root: RootRecord, activation: ActivationRecord, node: Node
) -> str:
    """The §13 test clause, on the first round of an opted-in rejecting node."""
    forced = (
        root.metadata.allow_test_flags
        and root.definition.document.instance.test_force_first_reject
        and Outcome.REJECT in (node.outcomes or ())
        and activation.metadata.round_no == FIRST_ROUND
    )
    return FORCED_FIRST_REJECT if forced else ""


def _checked_envelope(
    root: RootRecord,
    activation: ActivationRecord,
    node: Node,
    mandatory: str,
    inputs: tuple[Materialized, ...],
    *,
    supplied: frozenset[str],
) -> ComposedEnvelope:
    """Apply the node's byte budget to one brief and account for every omission.

    `inputs` are the ones this brief carries; `supplied` is every input the
    activation bound, so one already carried elsewhere is not "missing".
    """
    sources = root.index.sources
    bindings = {binding.name: binding for binding in activation.metadata.inputs}
    essential = root.metadata.essential_inputs or ()
    omissions = [item.omission for item in inputs if item.omission is not None]
    omissions.extend(
        InputOmission(name=name, reason="missing")
        for name in node.inputs or ()
        if name not in supplied and sources[name].optional
    )
    sections = []
    for item in inputs:
        if item.omission is not None:
            continue
        source = sources.get(item.name)
        binding = bindings.get(item.name)
        sections.append(
            EnvelopeSection(
                text=_labelled(item),
                name=item.name,
                optional=source.optional and item.name not in essential
                if source
                else False,
                trim_priority=source.trim_priority if source else 0,
                reference=binding.artifact_ref if binding else None,
                digest=binding.digest if binding else None,
            )
        )
    return compose_envelope(
        mandatory,
        tuple(sections),
        limit=node.context_budget_bytes or 262144,
        reference=f"wf-activation://{activation.activation_id}/envelope",
        omissions=tuple(omissions),
        limit_source="pinned" if node.context_budget_bytes else "legacy_safety_default",
        diagnostics=("legacy_token_budget_ignored",)
        if node.token_budget is not None
        else (),
    )


class ResumeDelta(BaseModel):
    """The steer text a continuation sends in place of any brief."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str
    included: tuple[str, ...]

    def envelope(self, fresh: ComposedEnvelope) -> ComposedEnvelope:
        """Account for the bytes the vendor got, not the brief it never saw.

        Only the budget the fresh composition ran under carries over: this
        text omitted no input, so the fresh brief's omissions are not its own.
        """
        return fresh.model_copy(
            update={
                "kind": EnvelopeKind.RESUME_DELTA,
                "text": self.text,
                "byte_count": len(self.text.encode("utf-8")),
                "included": self.included,
                "omissions": (),
                "sha256": hashlib.sha256(self.text.encode()).hexdigest(),
            }
        )


def _sent_bindings(prior: ActivationRecord) -> set[str]:
    """The bindings a turn's durable envelope record says the vendor received.

    Bound is not sent: the budget may have trimmed an input from that turn's
    brief, and the thread then never saw it. With no record, nothing counts.
    """
    record = prior.metadata.envelope
    included = None if record is None else record.get("included")
    if not isinstance(included, list):
        return set()
    names = {name for name in included if isinstance(name, str)}
    return {
        binding.model_dump_json()
        for binding in prior.metadata.inputs
        if binding.name in names
    }


def compose_resume_delta(
    root: RootRecord,
    activation: ActivationRecord,
    source: ActivationRecord,
    activations: Mapping[str, ActivationRecord],
    inputs: tuple[Materialized, ...],
) -> ComposedEnvelope:
    """Render this turn's facts, instructions and inputs the thread never received.

    Input identity is the complete immutable ``InputBinding``, and "received"
    is what each turn's durable envelope record says it SENT — so replaying
    this function after a crash produces the same delta without retaining
    prompt text or consulting live outputs. Protocol and leaf-contract sections
    belong only to a fresh envelope; the per-activation facts (this turn's id
    and round) do not, and are re-stated every turn.

    "The thread" is the whole RESUME CHAIN, not just the immediate source: the
    third turn of one vendor thread must not re-send what the first turn
    carried. The chain is walked through each source's own
    ``session_source_activation_id``, which is durable.

    The same byte budget as a fresh brief applies, and the returned envelope
    records the omissions THIS delta made — nothing it did not drop.
    """
    node = resolved_static_node(root, activation.metadata.node)
    sent: set[str] = set()
    seen: set[str] = set()
    prior: ActivationRecord | None = source
    while prior is not None and prior.activation_id not in seen:
        seen.add(prior.activation_id)
        sent.update(_sent_bindings(prior))
        source_id = prior.metadata.session_source_activation_id
        prior = activations.get(source_id) if source_id is not None else None
    new_inputs = tuple(
        item
        for binding, item in zip(activation.metadata.inputs, inputs, strict=True)
        if binding.model_dump_json() not in sent
    )
    mandatory = "\n\n".join(
        part.strip()
        for part in (
            RESUME_FACT_FRAME.format(
                activation_id=activation.activation_id,
                round_no=activation.metadata.round_no,
            ),
            _execution_identity(root, activation),
            node.instructions or "",
            (
                RESUMED_NON_WRITER_REVIEW_DELTA
                if activation.metadata.session_mode is SessionMode.RESUME
                and activation.metadata.source_session_id is not None
                and not node.writes
                else ""
            ),
            _forced_first_reject(root, activation, node),
        )
        if part.strip()
    )
    return _checked_envelope(
        root,
        activation,
        node,
        mandatory,
        new_inputs,
        supplied=frozenset(item.name for item in inputs),
    ).model_copy(update={"kind": EnvelopeKind.RESUME_DELTA})


class DefaultComposer:
    """Join materialized inputs and add the narrowly opted-in test clause."""

    def envelope(
        self,
        root: RootRecord,
        activation: ActivationRecord,
        inputs: tuple[Materialized, ...],
        *,
        instructions: str | None = None,
    ) -> ComposedEnvelope:
        """Compose the profile brief from immutable inputs and resolved flags."""
        node = resolved_static_node(root, activation.metadata.node)
        # One blank line between sections: the crew reads a document, not a
        # run-on. Each part is stripped so section spacing is the joiner's
        # job alone, whatever trailing newlines a template or input carries.
        brief = "\n\n".join(
            part.strip()
            for part in (
                _crew_protocol(node),
                _fact_frame(root, activation, node),
                LEAF_EXECUTION_CONTRACT,
                _execution_identity(root, activation),
                node.instructions or "",
                f"## Steer advice\n\n{instructions}"
                if instructions is not None
                else "",
                (
                    EVIDENCE_REFERENCE_INSTRUCTIONS
                    if node.artifact_input_mode is ArtifactInputMode.REFERENCES
                    else ""
                ),
            )
            if part.strip()
        )
        mandatory = "\n".join(
            filter(None, (brief, _forced_first_reject(root, activation, node)))
        )
        supplied = frozenset(item.name for item in inputs)
        essential = root.metadata.essential_inputs or ()
        if any(
            name not in supplied for name in essential if name in (node.inputs or ())
        ):
            raise InputsUnavailable("essential replacement advice is missing")
        return _checked_envelope(
            root, activation, node, mandatory, inputs, supplied=supplied
        )

    def compose(
        self,
        root: RootRecord,
        activation: ActivationRecord,
        inputs: tuple[Materialized, ...],
    ) -> str:
        """Compatibility text view of the complete checked envelope."""
        return self.envelope(root, activation, inputs).text
