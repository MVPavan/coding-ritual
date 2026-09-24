"""Root-row writes (§3.1) — pinning a graph into bd as an instance.

A root carries its own row id, which bd only assigns at create, so creating
one is two writes. `instance_key` closes the crash window between them: a
re-run finds the half-written root by key and completes it instead of starting
a second instance. The key is this wrapper's convention — §3.1 pins the body,
the hash and the resolved config, but names no creation key.

Reuse by key is an IDENTITY claim, not a cache hit: the same key with a
different graph or a different resolution is a different instance being
silently aliased onto an existing one, so it is refused. Two roots that
genuinely raced converge the way activations do (§3.2): lowest row id
survives, the loser is superseded, nothing is deleted.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

import structlog
from pydantic import TypeAdapter

from workflow_interpreter.bdio import finalize, reads
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.feedback import MSG_CONSUMER
from workflow_interpreter.bdio.records import RootRecord, parse_root
from workflow_interpreter.bdio.rows import NewRow, StoreRow
from workflow_interpreter.bdio.wire import (
    KEY_TERMINAL,
    KEY_WF_ROOT_ID,
    ConfigSource,
    InstanceInput,
    NodeSetting,
    ResolvedSetting,
    RootMetadata,
    config_signature,
    metadata_dict,
)
from workflow_interpreter.contracts.execution import (
    CREW_PREFIX,
    EXECUTION_POLICY_KEY,
    EXECUTION_POLICY_VERSION,
    EXECUTION_POLICY_VERSION_KEY,
    MSG_POLICY_MISMATCH,
    MSG_PROFILE_WRITES,
    MSG_UNREGISTERED_CREW,
    CrewName,
    ExecutionRegistry,
    UnregisteredCrewError,
    policy_for,
    tool_network_for,
)
from workflow_interpreter.contracts.run_identity import RunIdentity
from workflow_interpreter.contracts.sessions import (
    MSG_SESSION_REUSE,
    context_cap_key,
    session_mode_key,
)
from workflow_interpreter.schema.graph_index import producer_engine
from workflow_interpreter.schema.loader import canonical_bytes, load_pinned_body
from workflow_interpreter.schema.models import GraphDefinition, NodeKind

if TYPE_CHECKING:  # pragma: no cover - annotations only; the runtime
    # import direction is ledger -> bdio, so the store is named here and
    # never imported (R1: one implementation, not a protocol).
    from workflow_interpreter.ledger.store import LedgerStore

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

ROOT_SEQ: Final[int] = 0
MAX_INSTANCE_INPUT_BYTES: Final[int] = 65536
MAX_REPORTED_KEYS: Final[int] = 10
"""How many differing configuration keys a mismatch message names."""
_TITLE_ROOT: Final[str] = "wf root {graph_id} {instance_key}"
_REASON_ROOT_SUPERSEDED: Final[str] = "outcome=superseded superseded_by={winner}"
_REASON_ROOT_TERMINAL: Final[str] = "outcome=terminal terminal={terminal}"

_MSG_EMPTY_CONFIG: Final[str] = (
    "instance {instance_key!r} carries no resolved configuration; §3.1 "
    "requires every resolved profile, model, bound and isolation with its "
    "provenance — an empty resolution is an unrecorded one"
)
_MSG_REUSE_MISMATCH: Final[str] = (
    "instance_key={instance_key!r} already pins {field} {found!r}, requested "
    "{wanted!r}; reusing the key would alias a different instance onto it "
    "(§3.1) {detail}"
)
_FIELD_RESOLVED_CONFIG: Final[str] = "resolved_config"
_MSG_CONFIG_KEYS: Final[str] = "differing keys: {keys}"
_MSG_CONFIG_KEYS_TRUNCATED: Final[str] = "differing keys: {keys} (+{more} more)"
_MSG_INSTANCE_INPUT_BYTES: Final[str] = "instance inputs exceed {limit} bytes"
_MSG_TERMINAL_CONFLICT: Final[str] = (
    "root {root_id} already recorded terminal {found!r}; recording {wanted!r} "
    "would rewrite the settled end of the instance (§3.1)"
)
_MSG_NOT_A_TERMINAL: Final[str] = (
    "{terminal!r} is not a terminal node of the pinned graph of root {root_id}"
)
_MSG_SETTLE_SUPERSEDED: Final[str] = (
    "root {root_id} is superseded by {winner}; settling it on terminal "
    "{terminal!r} would overwrite the supersede close reason and resurrect a "
    "lost create race into instance truth (§3.1)"
)
_MSG_UNINSTRUCTED_TASKS: Final[str] = (
    "task nodes carry no instructions and cannot be dispatched: {nodes}"
)
_MSG_UNPINNED_TASK_EXECUTION_SETTINGS: Final[str] = (
    "task nodes carry no resolved execution setting pin and cannot be dispatched: {nodes}"
)
_MSG_DEFINITION_HASH_MISMATCH: Final[str] = (
    "definition content hash {declared!r} does not match canonical pinned body "
    "hash {actual!r}"
)


def _assert_tasks_are_instructed(definition: GraphDefinition) -> None:
    """Refuse a graph whose task nodes do not state what they must do (ADR 0002).

    This lives at `create_root` rather than at an authoring or link surface
    because `create_root` is the only chokepoint every root passes through:
    the CLI exposes no instantiate command, `instantiate()` is a private
    helper, and the test labs build roots by calling this directly. Enforcing
    anywhere else would leave §13 drills running on uninstructed roots.
    """
    uninstructed = tuple(
        node.name
        for node in definition.document.node
        if node.kind is NodeKind.TASK and not (node.instructions or "").strip()
    )
    if uninstructed:
        raise CarrierIntegrityError(
            _MSG_UNINSTRUCTED_TASKS.format(nodes=", ".join(uninstructed))
        )


def _assert_task_execution_settings_are_pinned(
    definition: GraphDefinition, resolved_config: Sequence[ResolvedSetting]
) -> None:
    """Refuse roots whose task mints or dispatches lack execution settings."""
    settings = {setting.key: setting.value for setting in resolved_config}
    unpinned: list[str] = []
    for node in definition.document.node:
        if node.kind is not NodeKind.TASK:
            continue
        # Root-time role resolution cannot prove which crew a role will bind.
        if node.session_reuse is not None and (
            (node.crew and node.crew.startswith(CREW_PREFIX))
            or settings.get(NodeSetting.CREW.at(node.name))
            != CrewName.CODEX_APPSERVER.value
        ):
            raise CarrierIntegrityError(MSG_SESSION_REUSE)
        role_bound = bool(node.crew and node.crew.startswith(CREW_PREFIX))
        required = (
            ()
            if role_bound and NodeSetting.CREW.at(node.name) not in settings
            else (NodeSetting.CREW, NodeSetting.MODEL, NodeSetting.EFFORT)
        )
        missing = [
            setting.value.rsplit(".", maxsplit=1)[-1]
            for setting in required
            if not (
                isinstance(value := settings.get(setting.at(node.name)), str)
                and value.strip()
            )
        ]
        mode = settings.get(session_mode_key(node.name))
        if (not role_bound or mode is not None) and (
            not isinstance(mode, str) or not mode.strip()
        ):
            missing.append("session_mode")
        if missing:
            unpinned.append(f"{node.name} ({', '.join(missing)})")
    if unpinned:
        raise CarrierIntegrityError(
            _MSG_UNPINNED_TASK_EXECUTION_SETTINGS.format(nodes=", ".join(unpinned))
        )


def pin_execution_policies(
    definition: GraphDefinition,
    resolved_config: Sequence[ResolvedSetting],
    *,
    profiles: ExecutionRegistry | None = None,
) -> tuple[ResolvedSetting, ...]:
    """Pin named authority before admission; preserve legacy settings verbatim."""
    execution_settings = {item.key: item for item in resolved_config}
    for node in definition.document.node:
        if node.execution_profile is None:
            continue
        version_key = EXECUTION_POLICY_VERSION_KEY.format(node=node.name)
        version = execution_settings.get(version_key)
        if version is not None and version.value != EXECUTION_POLICY_VERSION:
            raise CarrierIntegrityError(MSG_POLICY_MISMATCH)
        execution_settings[version_key] = ResolvedSetting(
            key=version_key,
            value=EXECUTION_POLICY_VERSION,
            source=ConfigSource.GRAPH_DEFAULT,
        )
        writes_key = NodeSetting.WRITES.at(node.name)
        writes = execution_settings.get(writes_key)
        if writes is not None and (
            writes.value != node.writes
            or writes.source is not ConfigSource.GRAPH_DEFAULT
        ):
            raise CarrierIntegrityError(MSG_PROFILE_WRITES)
        crew = execution_settings.get(NodeSetting.CREW.at(node.name))
        if crew is None and node.crew and node.crew.startswith(CREW_PREFIX):
            execution_settings[writes_key] = ResolvedSetting(
                key=writes_key,
                value=node.writes is True,
                source=ConfigSource.GRAPH_DEFAULT,
            )
            continue
        if crew is None or not isinstance(crew.value, str):
            raise CarrierIntegrityError(MSG_UNREGISTERED_CREW.format(crew=crew))
        try:
            execution_policy = policy_for(
                node.execution_profile, tool_network_for(crew.value, profiles)
            )
        except UnregisteredCrewError as error:
            raise CarrierIntegrityError(str(error)) from error
        key = EXECUTION_POLICY_KEY.format(node=node.name)
        expected = execution_policy.model_dump_json()
        if key in execution_settings and execution_settings[key].value != expected:
            raise CarrierIntegrityError(MSG_PROFILE_WRITES)
        execution_settings[key] = ResolvedSetting(
            key=key, value=expected, source=ConfigSource.GRAPH_DEFAULT
        )
        execution_settings[writes_key] = ResolvedSetting(
            key=writes_key,
            value=execution_policy.writes,
            source=ConfigSource.GRAPH_DEFAULT,
        )
    if any(node.execution_profile is not None for node in definition.document.node):
        return tuple(execution_settings[key] for key in sorted(execution_settings))
    return tuple(resolved_config)


def static_root_config(
    definition: GraphDefinition, settings: Sequence[ResolvedSetting]
) -> tuple[ResolvedSetting, ...]:
    """Project historical and new resolutions onto graph and static safety pins."""
    from workflow_interpreter.schema.decisions import DecisionTemplate

    roles = {
        node.name: node
        for node in definition.document.node
        if node.crew and node.crew.startswith(CREW_PREFIX)
    }
    projected: list[ResolvedSetting] = []
    for setting in settings:
        parts = setting.key.split(".")
        if len(parts) == 3 and parts[0] == "node" and parts[1] in roles:
            node = roles[parts[1]]
            is_role_derived_execution = setting.key in {
                NodeSetting.CREW.at(node.name),
                NodeSetting.MODEL.at(node.name),
                NodeSetting.EFFORT.at(node.name),
                context_cap_key(node.name),
            } and setting.source in {
                ConfigSource.ROLE_BINDING,
                ConfigSource.GRAPH_DEFAULT,
            }
            is_implicit_session_mode = (
                setting.key == session_mode_key(node.name) and node.session_mode is None
            )
            is_derived_policy = (
                setting.key == EXECUTION_POLICY_KEY.format(node=node.name)
                and setting.source is ConfigSource.GRAPH_DEFAULT
            )
            if (
                is_role_derived_execution
                or is_implicit_session_mode
                or is_derived_policy
            ):
                continue
        if len(parts) == 3 and parts[0] == "decision" and parts[2] == "template":
            template = DecisionTemplate.model_validate_json(str(setting.value))
            lowered = load_pinned_body(template.graph_body.encode())
            nested = static_root_config(
                lowered,
                TypeAdapter(tuple[ResolvedSetting, ...]).validate_json(
                    template.config_json
                ),
            )
            setting = setting.model_copy(
                update={
                    "value": template.model_copy(
                        update={
                            "config_json": TypeAdapter(tuple[ResolvedSetting, ...])
                            .dump_json(nested)
                            .decode()
                        }
                    ).model_dump_json()
                }
            )
        projected.append(setting)
    pinned_keys = {item.key for item in projected}
    for node in definition.document.node:
        if node.execution_profile is None:
            continue
        key = EXECUTION_POLICY_VERSION_KEY.format(node=node.name)
        if key not in pinned_keys:
            projected.append(
                ResolvedSetting(
                    key=key,
                    value=EXECUTION_POLICY_VERSION,
                    source=ConfigSource.GRAPH_DEFAULT,
                )
            )
    return tuple(projected)


def create_root(
    client: LedgerStore,
    *,
    instance_key: str,
    definition: GraphDefinition,
    resolved_config: Sequence[ResolvedSetting],
    instance_inputs: Sequence[InstanceInput] = (),
    allow_test_flags: bool = False,
    instance_base_commit: str | None = None,
    run_identity: RunIdentity | None = None,
    profiles: ExecutionRegistry | None = None,
) -> RootRecord:
    """Pin a graph into bd as a new instance (§3.1), idempotently by key.

    `run_identity` is the task and attempt this root IS (§3.7): pinned here so
    that every later reader — the verify environment above all — answers from
    the record rather than from a parse of the root id.
    """
    if not resolved_config:
        raise CarrierIntegrityError(_MSG_EMPTY_CONFIG.format(instance_key=instance_key))
    # Validate the pinned body and retain the resulting definition BEFORE
    # looking up an existing key: `create_root` is the programmatic entry
    # point and never runs the TOML loader, so a schema-invalid body could
    # reach bd and was only rejected afterwards by `_ensure_self_id` ->
    # `parse_root`. More subtly, a changed document carrying its old hash
    # could be mistaken for the same existing instance. The canonical body,
    # validated definition, and persisted hash are one exact pair.
    body = canonical_bytes(definition.document)
    validated_definition = load_pinned_body(body, allow_test_flags=allow_test_flags)
    if definition.content_hash != validated_definition.content_hash:
        raise CarrierIntegrityError(
            _MSG_DEFINITION_HASH_MISMATCH.format(
                declared=definition.content_hash,
                actual=validated_definition.content_hash,
            )
        )
    definition = validated_definition

    values = {item.key: item.value for item in resolved_config}
    engine_sources = {
        source.name
        for source in definition.document.source
        if producer_engine(source) is not None
    }
    for node in definition.document.node:
        if engine_sources.intersection(node.inputs or ()) and not values.get(
            NodeSetting.WRITES.at(node.name), node.writes
        ):
            raise CarrierIntegrityError(MSG_CONSUMER)
    resolved_config = pin_execution_policies(
        definition, resolved_config, profiles=profiles
    )
    existing = _root_for_key(client, instance_key)
    if existing is not None:
        _assert_same_instance(
            existing,
            instance_key,
            definition,
            resolved_config,
            instance_inputs,
            allow_test_flags,
            instance_base_commit,
        )
        return existing
    _assert_tasks_are_instructed(definition)
    _assert_task_execution_settings_are_pinned(definition, resolved_config)
    inputs = tuple(instance_inputs)
    if (
        sum(len(item.body.encode("utf-8")) for item in inputs)
        > MAX_INSTANCE_INPUT_BYTES
    ):
        raise CarrierIntegrityError(
            _MSG_INSTANCE_INPUT_BYTES.format(limit=MAX_INSTANCE_INPUT_BYTES)
        )
    from workflow_interpreter.schema.decisions import DecisionTemplate, lower_decision

    templates: dict[str, DecisionTemplate] = {}
    settings = {item.key: item.value for item in resolved_config}
    for node in definition.document.node:
        if node.token_budget is not None:
            _LOG.warning(
                "wf.context_budget.legacy_token_budget_ignored",
                node=node.name,
                limit_source="pinned"
                if settings.get(
                    f"node.{node.name}.context_budget_bytes", node.context_budget_bytes
                )
                else "legacy_safety_default",
            )
        policy = node.decision
        if policy is None:
            continue
        if definition.document.instance.coordination_limits is None:
            raise CarrierIntegrityError(
                "decision policy requires finite coordination limits"
            )
        if not settings.get(
            f"node.{node.name}.context_budget_bytes", node.context_budget_bytes
        ):
            raise CarrierIntegrityError("decision work requires context_budget_bytes")
        if "replace" in policy.actions:
            source = next(
                (
                    x
                    for x in definition.document.source
                    if x.name == policy.replacement_input
                ),
                None,
            )
            consumers = [
                n
                for n in definition.document.node
                if policy.replacement_input in (n.inputs or ())
            ]
            if (
                source is None
                or source.producer != "instance"
                or not source.optional
                or not consumers
            ):
                raise CarrierIntegrityError(
                    "replacement source must be optional instance input bound to work consumers"
                )
        raw = settings.get(f"decision.{node.name}.template")
        if not isinstance(raw, str):
            raise CarrierIntegrityError("decision task must be resolved at admission")
        template = DecisionTemplate.model_validate_json(raw)
        if (
            template.graph_body
            != canonical_bytes(lower_decision(policy).document).decode()
        ):
            raise CarrierIntegrityError(
                "decision template differs from pinned declaration"
            )
        templates[node.name] = template
    metadata = RootMetadata(
        instance_key=instance_key,
        graph_id=definition.document.graph.id,
        graph_version=definition.document.graph.version,
        graph_content_hash=definition.content_hash,
        graph_body=body.decode("utf-8"),
        resolved_config=tuple(resolved_config),
        instance_inputs=inputs,
        config_signature=config_signature(tuple(resolved_config)),
        allow_test_flags=allow_test_flags,
        instance_base_commit=instance_base_commit,
        run_identity=run_identity,
        seq=ROOT_SEQ,
        decision_templates=templates or None,
    )
    record = client._create_row(
        NewRow(
            summary=_TITLE_ROOT.format(
                graph_id=definition.document.graph.id, instance_key=instance_key
            ),
            metadata=metadata_dict(metadata),
        )
    )
    _LOG.info("wf.root.created", root_id=record.id, instance_key=instance_key)
    # `_create_row` resolves the §3.3 natural key inside `BEGIN IMMEDIATE` and
    # `roots.instance_key` is `NOT NULL UNIQUE`, so a concurrent create under
    # this key ANSWERS with the row that already exists — there is never a
    # second live root to converge (S6 review, finding 8).
    written = _ensure_self_id(client, record)
    # The row this create answered with may be someone ELSE's root: a
    # concurrent create under this key with a different graph or resolution
    # must be an identity error, exactly as reuse-by-key is. Without this, the
    # loser silently inherits an instance it did not configure (probed,
    # phase-2 review).
    _assert_same_instance(
        written,
        instance_key,
        definition,
        resolved_config,
        inputs,
        allow_test_flags,
        instance_base_commit,
    )
    return written


def _root_for_key(client: LedgerStore, instance_key: str) -> RootRecord | None:
    """The root this instance key already has, or nothing.

    ONE row or none, never a set to converge: `roots.instance_key` is
    `NOT NULL UNIQUE` and the natural key is resolved inside the create's own
    transaction, so the duplicate-root family this replaced could not fire on
    the one record store there is (S6 review, finding 8).

    Liveness is not read off a parsed record: a root whose create/self-link
    pair was interrupted does not parse yet, and completing it is exactly what
    this path exists for.
    """
    found = reads.find_roots(client, instance_key)
    if not found:
        return None
    return _ensure_self_id(client, found[0])


def _assert_same_instance(
    root: RootRecord,
    instance_key: str,
    definition: GraphDefinition,
    resolved_config: Sequence[ResolvedSetting],
    instance_inputs: Sequence[InstanceInput],
    allow_test_flags: bool,
    instance_base_commit: str | None,
) -> None:
    """Refuse to alias a different graph or resolution onto an existing key."""
    recorded_static = static_root_config(definition, root.metadata.resolved_config)
    requested_static = static_root_config(definition, resolved_config)
    comparisons = (
        (
            "graph_content_hash",
            root.metadata.graph_content_hash,
            definition.content_hash,
        ),
        ("instance_inputs", root.metadata.instance_inputs, tuple(instance_inputs)),
        ("allow_test_flags", root.metadata.allow_test_flags, allow_test_flags),
        (
            "instance_base_commit",
            root.metadata.instance_base_commit,
            instance_base_commit,
        ),
        (
            _FIELD_RESOLVED_CONFIG,
            config_signature(recorded_static),
            config_signature(requested_static),
        ),
    )
    for field, found, wanted in comparisons:
        if found != wanted:
            detail = (
                _differing_keys(recorded_static, requested_static)
                if field == _FIELD_RESOLVED_CONFIG
                else ""
            )
            raise CarrierIntegrityError(
                _MSG_REUSE_MISMATCH.format(
                    instance_key=instance_key,
                    field=field,
                    found=found,
                    wanted=wanted,
                    detail=detail,
                )
            )


def _differing_config_keys(
    recorded: Sequence[ResolvedSetting], requested: Sequence[ResolvedSetting]
) -> tuple[str, ...]:
    """Return the resolved-setting keys whose complete values differ."""
    by_key = {setting.key: setting for setting in recorded}
    other = {setting.key: setting for setting in requested}
    return tuple(
        sorted(
            key
            for key in by_key.keys() | other.keys()
            if by_key.get(key) != other.get(key)
        )
    )


def _differing_keys(
    recorded: Sequence[ResolvedSetting], requested: Sequence[ResolvedSetting]
) -> str:
    """Name the configuration keys the two resolutions disagree on, bounded.

    The digests alone are unactionable, and printing both whole resolutions is
    unbounded — the names are a debugging aid, the digests are the verdict.
    """
    differing = _differing_config_keys(recorded, requested)
    if not differing:
        return ""
    shown = differing[:MAX_REPORTED_KEYS]
    rendered = ", ".join(shown)
    if len(differing) > len(shown):
        return _MSG_CONFIG_KEYS_TRUNCATED.format(
            keys=rendered, more=len(differing) - len(shown)
        )
    return _MSG_CONFIG_KEYS.format(keys=rendered)


def _ensure_self_id(client: LedgerStore, row: StoreRow) -> RootRecord:
    """Complete the self-reference if the create/link pair was interrupted."""
    if row.metadata.get(KEY_WF_ROOT_ID) != row.id:
        row = client._merge_metadata(row.id, {KEY_WF_ROOT_ID: row.id})
    return parse_root(row)


def settle_root(client: LedgerStore, root_id: str, terminal: str) -> RootRecord:
    """Record the terminal this instance reached and close its root (§3.1).

    Metadata first, close second — the same order every §5.1 transition uses,
    for the same reason: a crash between the two leaves a root that already
    names its terminal, and the next call finishes the close. Re-recording the
    SAME terminal is a no-op; a different one is refused, because the end an
    instance reached is routing truth and is never rewritten.
    """
    record = parse_root(client.get_row(root_id))
    node = record.index.nodes.get(terminal)
    if node is None or node.kind is not NodeKind.TERMINAL:
        raise CarrierIntegrityError(
            _MSG_NOT_A_TERMINAL.format(terminal=terminal, root_id=root_id)
        )
    if record.metadata.is_superseded:
        # `close_forward` repairs a transition FORWARD, but only its own: this
        # root's close already landed as `outcome=superseded`, and re-driving
        # `bd close` overwrites the reason (probed). Refusing matches the
        # activation sibling (`api._MSG_CLOSE_SUPERSEDED`) — a lost race is
        # never reopened as routing truth.
        raise CarrierIntegrityError(
            _MSG_SETTLE_SUPERSEDED.format(
                root_id=root_id,
                winner=record.metadata.superseded_by,
                terminal=terminal,
            )
        )
    found = record.metadata.terminal
    if found is not None and found != terminal:
        raise CarrierIntegrityError(
            _MSG_TERMINAL_CONFLICT.format(root_id=root_id, found=found, wanted=terminal)
        )
    if found is None:

        def guard(row: StoreRow) -> None:
            """Re-assert "no other terminal" against the row being written.

            The check above ran against a read taken BEFORE this transaction,
            so two settlements that both saw an unset terminal would both pass
            it and the later one would rewrite the end of the instance. Handed
            to the backend so that a backend which can transact decides it
            against the row it is about to change (§3.3); bd does not evaluate
            it and keeps today's narrower window (`rows.RowGuard`).
            """
            recorded = row.metadata.get(KEY_TERMINAL)
            if recorded is not None and recorded != terminal:
                raise CarrierIntegrityError(
                    _MSG_TERMINAL_CONFLICT.format(
                        root_id=root_id, found=recorded, wanted=terminal
                    )
                )

        record = parse_root(
            client._merge_metadata(root_id, {KEY_TERMINAL: terminal}, guard=guard)
        )
        _LOG.info("wf.root.terminal", root_id=root_id, terminal=terminal)
    return finalize.close_record_forward(
        client,
        record,
        _REASON_ROOT_TERMINAL.format(terminal=terminal),
        parse_root,
    )
