"""Shared builders for the bdio test families (not a test module).

One definition of "a valid instance" and "a mint request", so the fake-bd and
live-bd families exercise the same shapes.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Final

from tests._helpers import VALID_FIXTURE
from workflow_interpreter import GraphDefinition, load_graph
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.records import (
    ActivationRecord,
    RootRecord,
    parse_activation,
)
from workflow_interpreter.bdio.wire import (
    ConfigSource,
    ExitRecord,
    Lifecycle,
    MintReason,
    MintRequest,
    ProcessHandle,
    ResolvedSetting,
)
from workflow_interpreter.schema.models import Outcome

REGION: Final[str] = "build-review"
IMPLEMENT: Final[str] = "implement"
REVIEW: Final[str] = "review"
SHIP: Final[str] = "ship"
TRIAGE: Final[str] = "triage"

RESOLVED_CONFIG: Final[tuple[ResolvedSetting, ...]] = (
    ResolvedSetting(
        key="instance.max_total_activations",
        value=20,
        source=ConfigSource.GRAPH_DEFAULT,
    ),
    ResolvedSetting(
        key="node.implement.runner",
        value="profile:implementer",
        source=ConfigSource.GRAPH_DEFAULT,
    ),
    ResolvedSetting(
        key="node.implement.model", value="default", source=ConfigSource.GRAPH_DEFAULT
    ),
    ResolvedSetting(
        key="node.implement.isolation",
        value="worktree",
        source=ConfigSource.GRAPH_DEFAULT,
    ),
)
"""A §3.1-shaped resolution: bounds, profile, model and isolation with
provenance. `create_root` refuses an empty one."""


REGION_A: Final[str] = "ra"
REGION_B: Final[str] = "rb"
NODE_A1: Final[str] = "a1"
NODE_B1: Final[str] = "b1"
NODE_B2: Final[str] = "b2"

CROSS_REGION_GRAPH: Final[str] = """
[graph]
id = "cross-region"
version = "1.0.0"
entry = "a1"
description = "one region routing into another at its entry node"

[instance]
max_total_activations = 40

[[region]]
name = "ra"
mode = "bounded-cycle"
entry_node = "a1"
max_entries = 3
on_exhausted = "triage"

[[region]]
name = "rb"
mode = "bounded-cycle"
entry_node = "b1"
max_entries = 2
on_exhausted = "triage"

[[node]]
name = "a1"
kind = "task"
region = "ra"
runner = "profile:x"
instructions = "Lab task node: do the thing this graph exists to test."
writes = false
allowed_paths = []
verify = [{ cmd = "scripts/verify.sh", timeout = "5m" }]
token_budget = 1000
max_wall = "10m"
stale_after = "5m"
max_infra_retries = 1
max_steers = 1
outcomes = ["done", "reject"]

[[node]]
name = "b2"
kind = "task"
region = "rb"
runner = "profile:x"
instructions = "Lab task node: do the thing this graph exists to test."
writes = false
allowed_paths = []
verify = [{ cmd = "scripts/verify.sh", timeout = "5m" }]
token_budget = 1000
max_wall = "10m"
stale_after = "5m"
max_infra_retries = 1
max_steers = 1
outcomes = ["done"]

[[node]]
name = "b1"
kind = "task"
region = "rb"
runner = "profile:x"
instructions = "Lab task node: do the thing this graph exists to test."
writes = false
allowed_paths = []
verify = [{ cmd = "scripts/verify.sh", timeout = "5m" }]
token_budget = 1000
max_wall = "10m"
stale_after = "5m"
max_infra_retries = 1
max_steers = 1
outcomes = ["done", "reject"]

[[node]]
name = "triage"
kind = "gate"
gate_type = "human"
binds = "immutable"
outcomes = ["rebudget", "abandon"]

[[node]]
name = "finished"
kind = "terminal"

[[edge]]
from = "a1"
on = "done"
to = "b1"

[[edge]]
from = "a1"
on = "reject"
to = "a1"

[[edge]]
from = "b1"
on = "done"
to = "b2"

[[edge]]
from = "b2"
on = "done"
to = "finished"

[[edge]]
from = "b1"
on = "reject"
to = "b1"

[[edge]]
from = "triage"
on = "rebudget"
to = "b1"

[[edge]]
from = "triage"
on = "abandon"
to = "finished"

[fallback]
to = "triage"
"""
"""Two bounded-cycle regions with a forward edge `a1 --done--> b1` crossing
from `ra` into `rb` at that region's `entry_node` — the only ingress §2 rule 6
permits. The §2 fixture cannot express this (it has one region), and it is the
shape in which `round_no` used to bleed across a region boundary, spending
`rb`'s rounds on arrivals `rb` never saw (probed, phase-2 review)."""


def load_definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed."""
    return load_graph(VALID_FIXTURE)


def load_cross_region(tmp_path: Path) -> GraphDefinition:
    """The two-region graph, materialized for the loader."""
    path = tmp_path / "cross-region.toml"
    path.write_text(CROSS_REGION_GRAPH, encoding="utf-8")
    return load_graph(path)


def instance_key() -> str:
    """A fresh instance key, so tests never share a root."""
    return f"it-{uuid.uuid4().hex[:12]}"


def make_root(
    store: WorkflowStore,
    definition: GraphDefinition,
    *overrides: ResolvedSetting,
) -> RootRecord:
    """Create a fresh instance whose resolution carries `overrides`."""
    replaced = {setting.key for setting in overrides}
    config = (
        tuple(setting for setting in RESOLVED_CONFIG if setting.key not in replaced)
        + overrides
    )
    return store.create_root(
        instance_key=instance_key(), definition=definition, resolved_config=config
    )


def handle(session_id: str = "sess-1") -> ProcessHandle:
    """A durable §5.3 process handle."""
    return ProcessHandle(
        pid=101,
        pgid=101,
        host="lab",
        host_boot_id="boot-1",
        proc_start_time="42",
        started_at="2026-08-25T00:00:00Z",
        log_path="/tmp/wf.jsonl",
        session_id=session_id,
    )


def run_to_close(
    store: WorkflowStore, activation_id: str, outcome: Outcome
) -> ActivationRecord:
    """Drive one activation through its whole §5.1 lifecycle to a close."""
    store.record_dispatch(activation_id, handle())
    store.record_exit(
        activation_id,
        ExitRecord(exit_code=0, ended_at="2026-08-25T00:01:00Z", reason="ok"),
    )
    return store.close_activation(activation_id, outcome)


def race_residue(
    client: BdClient, record: ActivationRecord, *, seq_delta: int = 1
) -> ActivationRecord:
    """A duplicate bead under the SAME idempotency key — real §3.2 race residue.

    What a lost single-flight lock leaves behind: two live activations for one
    key. `supersede_activation` now proves its winner shares the key, so a test
    about race resolution has to produce a genuine race rather than name an id
    that never existed.
    """
    duplicate = record.metadata.model_copy(
        update={
            "seq": record.metadata.seq + seq_delta,
            "lifecycle": Lifecycle.MINTED,
            "outcome": None,
            "evidence": None,
            "exit_record": None,
            "handle": None,
        }
    )
    return parse_activation(
        client._create_bead(
            title="wf race residue",
            metadata=duplicate.model_dump(mode="json", exclude_none=True),
        )
    )


def entry_request(**overrides: object) -> MintRequest:
    """An entry mint into the fixture's entry node."""
    base: dict[str, object] = {
        "node": IMPLEMENT,
        "mint_reason": MintReason.ENTRY,
        "runner_profile": "profile:implementer",
        "model": "default",
        "session_id": "sess-1",
    }
    return MintRequest.model_validate(base | overrides)
