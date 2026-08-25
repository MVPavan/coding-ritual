"""Root-bead writes (§3.1) — pinning a graph into bd as an instance.

A root carries its own bead id, which bd only assigns at create, so creating
one is two writes. `instance_key` closes the crash window between them: a
re-run finds the half-written root by key and completes it instead of starting
a second instance. The key is this wrapper's convention — §3.1 pins the body,
the hash and the resolved config, but names no creation key.

Reuse by key is an IDENTITY claim, not a cache hit: the same key with a
different graph or a different resolution is a different instance being
silently aliased onto an existing one, so it is refused. Two roots that
genuinely raced converge the way activations do (§3.2): lowest bead id
survives, the loser is superseded, nothing is deleted.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Final

import structlog
from pydantic import JsonValue

from workflow_interpreter.bdio import finalize, reads
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.records import RootRecord, parse_root
from workflow_interpreter.bdio.wire import (
    KEY_SUPERSEDED_BY,
    KEY_WF_ROOT_ID,
    BeadRecord,
    ResolvedSetting,
    RootMetadata,
    metadata_dict,
)
from workflow_interpreter.schema.loader import canonical_bytes, canonical_json_bytes
from workflow_interpreter.schema.models import GraphDefinition

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

ROOT_SEQ: Final[int] = 0
MAX_REPORTED_KEYS: Final[int] = 10
"""How many differing configuration keys a mismatch message names."""
_TITLE_ROOT: Final[str] = "wf root {graph_id} {instance_key}"
_REASON_ROOT_SUPERSEDED: Final[str] = "outcome=superseded superseded_by={winner}"

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
_MSG_ALL_SUPERSEDED: Final[str] = (
    "every root bead for instance_key={instance_key!r} is superseded"
)
_MSG_TWO_OWNING_ROOTS: Final[str] = (
    "instance_key={instance_key!r} has more than one live root owning instance "
    "beads ({owners}); converging would orphan a running instance — triage it "
    "(§3.1)"
)
_MSG_CONFIG_KEYS: Final[str] = "differing keys: {keys}"
_MSG_CONFIG_KEYS_TRUNCATED: Final[str] = "differing keys: {keys} (+{more} more)"


def create_root(
    client: BdClient,
    *,
    instance_key: str,
    definition: GraphDefinition,
    resolved_config: Sequence[ResolvedSetting],
) -> RootRecord:
    """Pin a graph into bd as a new instance (§3.1), idempotently by key."""
    if not resolved_config:
        raise CarrierIntegrityError(_MSG_EMPTY_CONFIG.format(instance_key=instance_key))
    existing = _converged_root(client, instance_key)
    if existing is not None:
        _assert_same_instance(existing, instance_key, definition, resolved_config)
        return existing
    metadata = RootMetadata(
        instance_key=instance_key,
        graph_id=definition.document.graph.id,
        graph_version=definition.document.graph.version,
        graph_content_hash=definition.content_hash,
        graph_body=canonical_bytes(definition.document).decode("utf-8"),
        resolved_config=tuple(resolved_config),
        seq=ROOT_SEQ,
    )
    record = client._create_bead(
        title=_TITLE_ROOT.format(
            graph_id=definition.document.graph.id, instance_key=instance_key
        ),
        metadata=metadata_dict(metadata),
    )
    _LOG.info("wf.root.created", root_id=record.id, instance_key=instance_key)
    _ensure_self_id(client, record)
    # Re-resolve after the write: a concurrent create under this key converges
    # HERE, rather than leaving two live instances for a later tick to find.
    converged = _converged_root(client, instance_key)
    if converged is None:  # pragma: no cover - the bead was just written
        raise CarrierIntegrityError(
            _MSG_ALL_SUPERSEDED.format(instance_key=instance_key)
        )
    # The convergence winner may be someone ELSE's root: a concurrent create
    # under this key with a different graph or resolution must be an identity
    # error, exactly as reuse-by-key is. Without this, the loser silently
    # inherits an instance it did not configure (probed, phase-2 review).
    _assert_same_instance(converged, instance_key, definition, resolved_config)
    return converged


def _converged_root(client: BdClient, instance_key: str) -> RootRecord | None:
    """The one live root for this key, superseding any concurrent duplicate.

    Liveness is read off the raw metadata, not a parsed record: a root whose
    create/self-link pair was interrupted does not parse yet, and completing
    it is exactly what this path exists for.
    """
    found = reads.find_roots(client, instance_key)
    live = [bead for bead in found if bead.metadata.get(KEY_SUPERSEDED_BY) is None]
    if not live:
        if found:
            raise CarrierIntegrityError(
                _MSG_ALL_SUPERSEDED.format(instance_key=instance_key)
            )
        return None
    winner, *losers = _ordered_by_ownership(client, live, instance_key)
    for loser in losers:
        _supersede_root(client, loser, winner.id)
    return _ensure_self_id(client, winner)


def _ordered_by_ownership(
    client: BdClient, live: Sequence[BeadRecord], instance_key: str
) -> tuple[BeadRecord, ...]:
    """Convergence order for duplicate roots: the OWNER of the instance first (§3.1).

    Bead ids are not ordered by creation (bd 1.1.0 hands out `wf-yd1` before
    `wf-c7b`; probed, phase-2 r3), so "lowest id survives" says nothing about
    which root the instance actually ran on. A root that already owns
    activations and gates is never superseded — closing it would orphan the
    whole trace under a root nothing links to. Among roots that own nothing the
    lowest id still wins, so two ticks resolving the same residue agree.
    """
    if len(live) < 2:
        return tuple(live)
    owners = [bead for bead in live if _owns_instance_beads(client, bead.id)]
    if len(owners) > 1:
        raise CarrierIntegrityError(
            _MSG_TWO_OWNING_ROOTS.format(
                instance_key=instance_key,
                owners=", ".join(sorted(bead.id for bead in owners)),
            )
        )
    if not owners:
        return tuple(live)
    owner = owners[0]
    return (owner, *(bead for bead in live if bead.id != owner.id))


def _owns_instance_beads(client: BdClient, root_id: str) -> bool:
    """Whether any activation, gate or event of the instance links to this root."""
    return any(bead.id != root_id for bead in reads.instance_beads(client, root_id))


def _supersede_root(client: BdClient, loser: BeadRecord, winner_id: str) -> None:
    """Close a duplicate root append-only, pointing at the surviving one."""
    record = _ensure_self_id(client, loser)
    metadata = record.metadata.model_copy(update={"superseded_by": winner_id})
    updated = client._merge_metadata(loser.id, metadata_dict(metadata))
    finalize.close_forward(
        client, updated, _REASON_ROOT_SUPERSEDED.format(winner=winner_id)
    )
    _LOG.warning("wf.root.superseded", loser=loser.id, winner=winner_id)


def _assert_same_instance(
    root: RootRecord,
    instance_key: str,
    definition: GraphDefinition,
    resolved_config: Sequence[ResolvedSetting],
) -> None:
    """Refuse to alias a different graph or resolution onto an existing key."""
    comparisons = (
        (
            "graph_content_hash",
            root.metadata.graph_content_hash,
            definition.content_hash,
        ),
        (
            _FIELD_RESOLVED_CONFIG,
            _config_signature(root.metadata.resolved_config),
            _config_signature(resolved_config),
        ),
    )
    for field, found, wanted in comparisons:
        if found != wanted:
            detail = (
                _differing_keys(root.metadata.resolved_config, resolved_config)
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


def _differing_keys(
    recorded: Sequence[ResolvedSetting], requested: Sequence[ResolvedSetting]
) -> str:
    """Name the configuration keys the two resolutions disagree on, bounded.

    The digests alone are unactionable, and printing both whole resolutions is
    unbounded — the names are a debugging aid, the digests are the verdict.
    """
    by_key = {setting.key: setting for setting in recorded}
    other = {setting.key: setting for setting in requested}
    differing = sorted(
        key for key in by_key.keys() | other.keys() if by_key.get(key) != other.get(key)
    )
    if not differing:
        return ""
    shown = differing[:MAX_REPORTED_KEYS]
    rendered = ", ".join(shown)
    if len(differing) > len(shown):
        return _MSG_CONFIG_KEYS_TRUNCATED.format(
            keys=rendered, more=len(differing) - len(shown)
        )
    return _MSG_CONFIG_KEYS.format(keys=rendered)


def _config_signature(settings: Sequence[ResolvedSetting]) -> str:
    """An order-independent identity digest of a resolved configuration.

    Order-independent because resolution order carries no meaning. A root's
    `resolved_config` is written once, at create, and never again — a §10.4
    rebudget records its raise on the gate bead — so the live resolution IS
    the creation-time one and a re-tick under the original config stays
    idempotent. A separately recorded creation signature existed only to
    survive the root-config write that no longer happens.

    Values are hashed with their JSON TYPE, never through `str()`: stringifying
    made the integer `1` and the string `"1"` (and `True` and `"True"`) the
    same instance, so a re-tick under a differently TYPED resolution silently
    reused a root configured otherwise (probed, phase-2 r3). Ordering is by the
    entry's canonical encoding, which is total across mixed value types where
    tuple comparison is not.
    """
    entries: list[list[JsonValue]] = [
        [setting.key, setting.value, setting.source.value] for setting in settings
    ]
    ordered = sorted(entries, key=canonical_json_bytes)
    return hashlib.sha256(canonical_json_bytes(ordered)).hexdigest()


def _ensure_self_id(client: BdClient, bead: BeadRecord) -> RootRecord:
    """Complete the self-reference if the create/link pair was interrupted."""
    if bead.metadata.get(KEY_WF_ROOT_ID) != bead.id:
        bead = client._merge_metadata(bead.id, {KEY_WF_ROOT_ID: bead.id})
    return parse_root(bead)
