"""S4: the debrief contract, its verifier, re-verification and archive.

Four claims, each tested where it is decidable:

- `scripts/verify-debrief.sh` contains a debrief to one directory and refuses a
  file that is not the render — run for real, against a real git history;
- the render is deterministic, pinned before the node that must copy it runs,
  and a debrief the host refuses reaches `triage`, never `ship`;
- `wf ledger verify` re-verifies a task's approvals from the committed export
  with the ledger database and the wrapper root gone, and a tampered byte is
  refused;
- `wf archive` deletes nothing without a bundle git itself accepts, and the
  bundle it does accept restores the refs.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from tests._bdio import entry_request, handle, load_definition, make_root
from tests._foreman import LAB_ATTEMPT, LAB_TASK, ForemanLab
from tests._gates import approval_payload, close
from tests._helpers import AUTHORING_FIXTURE
from tests._inspector import ChildScript, make_repo
from tests._ledger import TASK, ledger_store, repository, seed_contractor_record
from tests.conftest import Signer
from tests.test_ledger_writes import EXIT_RECORD, _open_gate
from workflow_interpreter import load_graph
from workflow_interpreter.bdio import GateVerifier, Outcome, SigningConfig
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.carriers import (
    LEDGER_RENDER_REF,
    Evidence,
    ProcessHandle,
    Severity,
)
from workflow_interpreter.bdio.findings import (
    MAX_FINDING_BYTES,
    MAX_REVIEW_FINDINGS_BYTES,
    REVIEW_NO_FINDINGS,
    REVIEW_REPORT_FILE,
    TEXT_REVIEW_ABSENT,
    TRUNCATION_MARKER,
    FindingKind,
    findings_of,
)
from workflow_interpreter.bdio.records import ActivationRecord, RootRecord
from workflow_interpreter.bdio.signing import key_fingerprint
from workflow_interpreter.bdio.wire import ActivationMetadata
from workflow_interpreter.contracts.run_identity import RunIdentity
from workflow_interpreter.foreman.config import wrapper_root_for
from workflow_interpreter.foreman.ledger_render import (
    EVIDENCE_FILE,
    FINDINGS_FILE,
    render_run,
)
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.exit_grade import (
    MAX_REVIEW_ARTIFACT_BYTES,
    review_findings,
)
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.launch_record import LaunchReceipt
from workflow_interpreter.inspector.paths import write_record
from workflow_interpreter.inspector.procfs import read_boot_id, read_start_time
from workflow_interpreter.inspector.verify import (
    ATTEMPT_ENV,
    BASE_COMMIT_ENV,
    EPIC_SEGMENT_ENV,
    RENDER_DIGEST_ENV,
    RENDER_OID_ENV,
    TASK_ID_ENV,
)
from workflow_interpreter.ledger.archive import archive_task
from workflow_interpreter.ledger.constants import (
    EXPORT_REF_TEMPLATE,
    EXPORT_SUFFIX,
    ExportKey,
    LedgerTable,
    TaskState,
)
from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.export import import_export, write_export
from workflow_interpreter.ledger.paths import export_path, ledger_path
from workflow_interpreter.ledger.reverify import (
    ExportAnchor,
    TrustAnchor,
    read_signatures,
    verify_approvals,
    verify_export,
    verify_signature,
)
from workflow_interpreter.ledger.tasks import (
    ensure_task,
    record_export_oid,
    record_task_state,
)
from workflow_interpreter.schema.models import Node

VERIFY_DEBRIEF: Final[Path] = (
    Path(__file__).resolve().parents[1] / "scripts" / "verify-debrief.sh"
)
SCRIPT_TIMEOUT_S: Final[float] = 60.0
GIT_TIMEOUT_S: Final[float] = 60.0
DEBRIEF_FILE: Final[str] = "debrief.md"
DEBRIEF_BODY: Final[str] = "# Debrief\n\nWhat happened, and why.\n"
FINDINGS_BODY: Final[str] = "# Findings\n\nround one\n"
EVIDENCE_BODY: Final[str] = '{"version":1}\n'
TASK_ID: Final[str] = "cr-3411.5"
EPIC_ID: Final[str] = "cr-3411"
"""The epic the lab's task belongs under — stated, never parsed out of the
task id (§3.7, R8)."""
OTHER_TASK: Final[str] = "cr-3411.9"
"""A second ledger task, whose export is a valid export of something else."""
ATTEMPT: Final[int] = 1
DEBRIEF_MAX_BYTES: Final[int] = 16384
PASSING: Final[str] = "#!/bin/sh\nexit 0\n"
FAILING: Final[str] = "#!/bin/sh\nexit 1\n"
DONE_MARKER: Final[str] = '{"outcome":"done"}\n'
NO_DIFF_MARKER: Final[str] = '{"outcome":"no_diff"}\n'
REJECT_MARKER: Final[str] = '{"outcome":"reject"}\n'
NO_EFFECTS: Final[str] = '{"paths":[]}'
FEATURE: Final[str] = "src/feature.py"


def _git(repo: Path, *args: str) -> str:
    """One git command in a throwaway repository."""
    return (
        subprocess.check_output(
            ["git", *args], cwd=repo, timeout=GIT_TIMEOUT_S, stderr=subprocess.STDOUT
        )
        .decode()
        .strip()
    )


def _attempt_dir(repo: Path, task_id: str = TASK_ID, attempt: int = ATTEMPT) -> Path:
    """The one directory a debrief of this run may write."""
    return repo / "docs" / "workstreams" / EPIC_ID / "runs" / task_id / f"a{attempt}"


def _pin_render(repo: Path, tmp_path: Path) -> None:
    """Pin `findings.md` and `evidence.json` under this run's render ref.

    Written with the same plumbing the engine uses — hash-object, a throwaway
    index, write-tree, commit-tree — so the ref the check resolves is the shape
    `bind_render` produces rather than a convenient stand-in.
    """
    staging = tmp_path / "render"
    staging.mkdir(exist_ok=True)
    (staging / FINDINGS_FILE).write_text(FINDINGS_BODY, encoding="utf-8")
    (staging / EVIDENCE_FILE).write_text(EVIDENCE_BODY, encoding="utf-8")
    environment = {
        **os.environ,
        "GIT_INDEX_FILE": str(tmp_path / "render.index"),
        "GIT_AUTHOR_NAME": "wf",
        "GIT_AUTHOR_EMAIL": "wf@test",
        "GIT_COMMITTER_NAME": "wf",
        "GIT_COMMITTER_EMAIL": "wf@test",
    }

    def plumbing(*args: str) -> str:
        return (
            subprocess.check_output(
                ["git", *args], cwd=repo, timeout=GIT_TIMEOUT_S, env=environment
            )
            .decode()
            .strip()
        )

    for name in (FINDINGS_FILE, EVIDENCE_FILE):
        oid = plumbing("hash-object", "-w", "--no-filters", "--", str(staging / name))
        plumbing("update-index", "--add", "--cacheinfo", f"100644,{oid},{name}")
    commit = plumbing("commit-tree", plumbing("write-tree"), "-m", "render")
    _git(
        repo,
        "update-ref",
        LEDGER_RENDER_REF.format(task_id=TASK_ID, attempt=ATTEMPT),
        commit,
    )


@pytest.fixture
def debrief_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository at a known base commit whose render ref is pinned."""
    repo = tmp_path / "debrief-repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "--quiet", "--initial-branch=main")
    _git(repo, "config", "user.email", "wf@test")
    _git(repo, "config", "user.name", "wf test")
    (repo / "README.md").write_text("start\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "initial")
    _pin_render(repo, tmp_path)
    return repo, _git(repo, "rev-parse", "HEAD")


def _render_oid(repo: Path) -> str:
    """The render TREE the engine would have pinned in the activation carrier.

    Resolved from the ref HERE, in the harness, because in production the id
    comes from the activation's `LedgerRenderBinding` and the script is given
    the id alone — which is the whole point of `WF_RENDER_OID`.
    """
    ref = LEDGER_RENDER_REF.format(task_id=TASK_ID, attempt=ATTEMPT)
    return _git(repo, "rev-parse", f"{ref}^{{tree}}")


def _render_digest() -> str:
    """The binding's digest over both rendered files, findings first."""
    return hashlib.sha256(
        FINDINGS_BODY.encode("utf-8") + EVIDENCE_BODY.encode("utf-8")
    ).hexdigest()


def _run_debrief_check(
    repo: Path,
    base: str,
    *,
    task_id: str = TASK_ID,
    epic_id: str = EPIC_ID,
    attempt: str = str(ATTEMPT),
    render_oid: str | None = None,
    render_digest: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the real verifier exactly as the wrapper does: env, no arguments."""
    return subprocess.run(
        [str(VERIFY_DEBRIEF)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_S,
        check=False,
        env={
            **os.environ,
            BASE_COMMIT_ENV: base,
            EPIC_SEGMENT_ENV: epic_id,
            TASK_ID_ENV: task_id,
            ATTEMPT_ENV: attempt,
            RENDER_OID_ENV: (_render_oid(repo) if render_oid is None else render_oid),
            RENDER_DIGEST_ENV: (
                _render_digest() if render_digest is None else render_digest
            ),
        },
    )


def _write_debrief(
    repo: Path,
    *,
    debrief: str = DEBRIEF_BODY,
    findings: str = FINDINGS_BODY,
    stray: str | None = None,
) -> str:
    """Commit one debrief round, optionally with a file outside its directory."""
    directory = _attempt_dir(repo)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / DEBRIEF_FILE).write_text(debrief, encoding="utf-8")
    (directory / FINDINGS_FILE).write_text(findings, encoding="utf-8")
    (directory / EVIDENCE_FILE).write_text(EVIDENCE_BODY, encoding="utf-8")
    if stray is not None:
        path = repo / stray
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not mine to write\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "debrief")
    return _git(repo, "rev-parse", "HEAD")


# --- the verifier, run for real (§3.7) --------------------------------------


def test_a_contained_debrief_that_copies_its_render_passes(
    debrief_repo: tuple[Path, str],
) -> None:
    """The happy path: three files, one directory, the render byte for byte."""
    repo, base = debrief_repo
    _write_debrief(repo)

    result = _run_debrief_check(repo, base)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS debrief-containment" in result.stdout
    assert "PASS debrief-render" in result.stdout


def test_a_debrief_that_writes_outside_its_directory_is_refused(
    debrief_repo: tuple[Path, str],
) -> None:
    """Containment is the verifier's job, not the grant's (ADR 0001, §3.7)."""
    repo, base = debrief_repo
    _write_debrief(repo, stray="src/sneaky.py")

    result = _run_debrief_check(repo, base)

    assert result.returncode != 0
    assert "FAIL debrief-containment" in result.stdout
    assert "src/sneaky.py" in result.stdout


def test_a_findings_file_that_differs_from_the_render_is_refused(
    debrief_repo: tuple[Path, str],
) -> None:
    """The rendered files are the ledger's, and a debrief may not edit them."""
    repo, base = debrief_repo
    _write_debrief(repo, findings=FINDINGS_BODY + "and my own opinion\n")

    result = _run_debrief_check(repo, base)

    assert result.returncode != 0
    assert "FAIL debrief-render" in result.stdout


def test_a_missing_debrief_file_is_refused(debrief_repo: tuple[Path, str]) -> None:
    """Three files, or the round did not happen."""
    repo, base = debrief_repo
    _write_debrief(repo)
    (_attempt_dir(repo) / DEBRIEF_FILE).unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "drop the debrief")

    result = _run_debrief_check(repo, base)

    assert result.returncode != 0
    assert "FAIL debrief-files" in result.stdout


def test_an_oversized_debrief_is_refused(debrief_repo: tuple[Path, str]) -> None:
    """The size bound is stated, so a node can obey it and a reader rely on it."""
    repo, base = debrief_repo
    _write_debrief(repo, debrief="x" * (DEBRIEF_MAX_BYTES + 1))

    result = _run_debrief_check(repo, base)

    assert result.returncode != 0
    assert "FAIL debrief-size" in result.stdout


def test_an_empty_run_identity_refuses_instead_of_guessing_a_path(
    debrief_repo: tuple[Path, str],
) -> None:
    """A wiring that pinned no identity must not pass a check by default."""
    repo, base = debrief_repo
    _write_debrief(repo)

    result = _run_debrief_check(repo, base, task_id="")

    assert result.returncode != 0
    assert "FAIL debrief-identity" in result.stdout


def test_an_activation_with_no_render_pin_skips_the_comparison_loudly(
    debrief_repo: tuple[Path, str],
) -> None:
    """`review` runs this check with no render of its own, and says so.

    An engine source may only be consumed by a WRITING node
    (`bdio/roots.py`, MSG_CONSUMER), so the reviewer is bound no render. It
    still grades containment, presence, modes and size; the render comparison
    belongs to the activation the engine pinned one for.
    """
    repo, base = debrief_repo
    _write_debrief(repo)

    result = _run_debrief_check(repo, base, render_oid="", render_digest="")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SKIP debrief-render" in result.stdout
    assert "PASS debrief-containment" in result.stdout
    assert "PASS debrief-files" in result.stdout


def test_a_repointed_render_ref_cannot_redefine_the_expected_bytes(
    debrief_repo: tuple[Path, str],
) -> None:
    """Finding 1: the check reads the OID the activation pinned, not a ref.

    The ref is moved to an attacker's render and the landed files are made to
    match it. If the check resolved the ref by name this would pass; because it
    is given the pinned tree id, the landed files no longer match the render.
    """
    repo, base = debrief_repo
    pinned = _render_oid(repo)
    forged = FINDINGS_BODY + "and my own opinion\n"
    _write_debrief(repo, findings=forged)
    staging = repo.parent / "forged"
    staging.mkdir(exist_ok=True)
    (staging / FINDINGS_FILE).write_text(forged, encoding="utf-8")
    (staging / EVIDENCE_FILE).write_text(EVIDENCE_BODY, encoding="utf-8")
    environment = {
        **os.environ,
        "GIT_INDEX_FILE": str(repo.parent / "forged.index"),
        "GIT_AUTHOR_NAME": "attacker",
        "GIT_AUTHOR_EMAIL": "attacker@wf",
        "GIT_COMMITTER_NAME": "attacker",
        "GIT_COMMITTER_EMAIL": "attacker@wf",
    }

    def plumbing(*args: str) -> str:
        return (
            subprocess.check_output(
                ["git", *args], cwd=repo, timeout=GIT_TIMEOUT_S, env=environment
            )
            .decode()
            .strip()
        )

    for name in (FINDINGS_FILE, EVIDENCE_FILE):
        oid = plumbing("hash-object", "-w", "--no-filters", "--", str(staging / name))
        plumbing("update-index", "--add", "--cacheinfo", f"100644,{oid},{name}")
    commit = plumbing("commit-tree", plumbing("write-tree"), "-m", "forged render")
    _git(
        repo,
        "update-ref",
        LEDGER_RENDER_REF.format(task_id=TASK_ID, attempt=ATTEMPT),
        commit,
    )

    assert _render_oid(repo) != pinned
    result = _run_debrief_check(repo, base, render_oid=pinned)

    assert result.returncode != 0
    assert "FAIL debrief-render" in result.stdout


def test_a_render_whose_digest_is_not_the_pinned_one_is_refused(
    debrief_repo: tuple[Path, str],
) -> None:
    """Finding 1: the payload digest of the binding is checked, not assumed."""
    repo, base = debrief_repo
    _write_debrief(repo)

    result = _run_debrief_check(repo, base, render_digest="0" * 64)

    assert result.returncode != 0
    assert "FAIL debrief-render" in result.stdout
    assert "pinned" in result.stdout


def test_a_committed_symlink_in_place_of_a_rendered_file_is_refused(
    debrief_repo: tuple[Path, str],
) -> None:
    """Finding 3: mode 120000 passes every byte comparison and is not the file.

    `findings.md` is committed as a symlink to a file OUTSIDE the attempt
    directory that holds the render's bytes: `cmp` through the working tree
    would be satisfied, and the landed artifact would still carry no findings.
    """
    repo, base = debrief_repo
    _write_debrief(repo)
    directory = _attempt_dir(repo)
    (repo / "elsewhere.md").write_text(FINDINGS_BODY, encoding="utf-8")
    (directory / FINDINGS_FILE).unlink()
    (directory / FINDINGS_FILE).symlink_to(repo / "elsewhere.md")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "a symlink instead of the findings")

    result = _run_debrief_check(repo, base)

    assert result.returncode != 0
    assert "FAIL debrief" in result.stdout
    assert "120000" in result.stdout or "outside" in result.stdout


def test_a_symlink_beside_the_three_files_is_refused(
    debrief_repo: tuple[Path, str],
) -> None:
    """Finding 3: the whole permitted directory is swept, not the three names."""
    repo, base = debrief_repo
    _write_debrief(repo)
    (_attempt_dir(repo) / "link").symlink_to(repo / "README.md")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "a stray symlink")

    result = _run_debrief_check(repo, base)

    assert result.returncode != 0
    assert "FAIL debrief-files" in result.stdout
    assert "120000" in result.stdout


@pytest.mark.parametrize(
    "task_id", ["../../../etc", "cr-3411/../..", ".hidden", "cr .*", ""]
)
def test_an_unsafe_task_id_never_widens_containment(
    debrief_repo: tuple[Path, str], task_id: str
) -> None:
    """Finding 4: an identity is one safe path component or it is refused."""
    repo, base = debrief_repo
    _write_debrief(repo)

    result = _run_debrief_check(repo, base, task_id=task_id)

    assert result.returncode != 0
    assert "FAIL debrief-identity" in result.stdout


@pytest.mark.parametrize("attempt", ["0", "-1", "1x", ""])
def test_an_unusable_attempt_is_refused(
    debrief_repo: tuple[Path, str], attempt: str
) -> None:
    """Finding 4: attempts start at one, and are digits."""
    repo, base = debrief_repo
    _write_debrief(repo)

    result = _run_debrief_check(repo, base, attempt=attempt)

    assert result.returncode != 0
    assert "FAIL debrief-identity" in result.stdout


@pytest.mark.parametrize(
    ("task_id", "attempt"), [("../x", 1), ("a/b", 1), (".git", 1), ("ok", 0)]
)
def test_the_record_refuses_an_identity_a_path_cannot_hold(
    task_id: str, attempt: int
) -> None:
    """Finding 4: the same rule on the record, so nothing unsafe is ever pinned."""
    with pytest.raises(ValidationError):
        RunIdentity(task_id=task_id, epic_id=EPIC_ID, attempt=attempt)


def test_an_abandoned_attempt_keeps_a1_while_a2_lands(
    debrief_repo: tuple[Path, str],
) -> None:
    """A fresh attempt writes beside the abandoned one, never over it (§3.8)."""
    repo, _ = debrief_repo
    abandoned = _write_debrief(repo)
    first = _attempt_dir(repo).relative_to(repo)

    second = _attempt_dir(repo, attempt=2)
    second.mkdir(parents=True)
    (second / DEBRIEF_FILE).write_text(DEBRIEF_BODY, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "second attempt")

    assert (repo / first / DEBRIEF_FILE).is_file()
    assert (second / DEBRIEF_FILE).is_file()
    # The abandoned attempt's own commit still holds its whole directory.
    landed = _git(repo, "show", "--name-only", "--format=", abandoned)
    assert f"{first}/{DEBRIEF_FILE}" in landed


# --- the graph (§3.7) --------------------------------------------------------


def test_the_shipped_graph_routes_a_failed_debrief_to_triage() -> None:
    """`fail_code` and `fail_plan` leave the debrief at a human, never at ship."""
    graph = load_graph(AUTHORING_FIXTURE)
    edges = {(edge.from_node, edge.on.value): edge.to for edge in graph.document.edge}

    assert graph.warnings == ()
    assert edges[("implement", "done")] == "debrief"
    assert edges[("debrief", "done")] == "review"
    assert edges[("debrief", "no_diff")] == "review"
    assert edges[("debrief", "fail_code")] == "triage"
    assert edges[("debrief", "fail_plan")] == "triage"
    assert not any(
        edge.from_node == "debrief" and edge.to == "ship"
        for edge in graph.document.edge
    )
    debrief = next(node for node in graph.document.node if node.name == "debrief")
    review = next(node for node in graph.document.node if node.name == "review")
    assert debrief.allowed_paths == ("docs/workstreams/**",)
    assert debrief.inputs is not None and "ledger_render" in debrief.inputs
    own = {check.cmd for check in debrief.verify or ()}
    assert own == {"scripts/verify-debrief.sh"}
    assert own < {check.cmd for check in review.verify or ()}


# --- the render and the node that must copy it -------------------------------


def _lab(tmp_path: Path, signing: SigningConfig, signer: Signer) -> ForemanLab:
    """A lab on the SHIPPED graph, which is the one with a debrief node."""
    return ForemanLab(tmp_path, toml=AUTHORING_FIXTURE, signing=signing, signer=signer)


def _implement(lab: ForemanLab) -> None:
    """One `implement` round that commits a feature and claims `done`."""
    lab.profiles.next_script(
        ChildScript(
            marker=DONE_MARKER,
            effects=f'{{"paths":["{FEATURE}"]}}',
            write_path=FEATURE,
            write_body="value = 2\n",
            commit=True,
        )
    )
    assert lab.tick().dispatched is not None
    assert lab.tick().settled is not None


def test_the_render_is_the_same_bytes_every_time(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Two renders of one unchanged instance agree — the check depends on it."""
    lab = _lab(tmp_path, signing_config, sign_payload)
    root = lab.instantiate()
    activations = lab.store.reads.list_activations(root.root_id)
    gates = lab.store.reads.list_gates(root.root_id)

    first = render_run(root, activations, gates, round_no=1)
    second = render_run(root, activations, gates, round_no=1)

    assert first == second
    assert first.payload_digest == second.payload_digest
    evidence = json.loads(first.evidence_json)
    assert (evidence["task_id"], evidence["attempt"]) == (LAB_TASK, LAB_ATTEMPT)
    assert LAB_TASK in first.findings_md


def test_the_render_ref_is_pinned_before_the_debrief_runs(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """The bytes a debrief is judged against exist before it is asked to write."""
    lab = _lab(tmp_path, signing_config, sign_payload)
    lab.instantiate()
    _implement(lab)
    lab.profiles.next_script(ChildScript(marker=NO_DIFF_MARKER, effects=NO_EFFECTS))
    debrief_id = lab.tick().dispatched
    assert debrief_id is not None

    ref = LEDGER_RENDER_REF.format(task_id=LAB_TASK, attempt=LAB_ATTEMPT)
    assert lab.git.ref_target(ref, cwd=lab.repo) is not None
    bound = lab.store.reads.load_activation(debrief_id).metadata.inputs
    render = next(item for item in bound if item.name == "ledger_render")
    assert render.ledger_render is not None
    assert render.artifact_ref == ref
    assert _git(lab.repo, "cat-file", "blob", f"{ref}:{FINDINGS_FILE}")


def test_a_debrief_the_host_refuses_reaches_triage_and_never_ship(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """The graph's answer to a debrief that failed its verifier (§3.7, D12).

    The verifier is red here rather than subtly wrong, because WHY it is red —
    a stray path, an edited render — is settled by the tests above against the
    real script. What this proves is the routing: a red debrief grades
    `fail_code` over its own `done` claim and ends at a human.
    """
    lab = _lab(tmp_path, signing_config, sign_payload)
    lab.pin_checks(
        {
            "scripts/verify-feature.sh": PASSING,
            "scripts/review-checks.sh": PASSING,
            "scripts/verify-debrief.sh": FAILING,
        }
    )
    lab.instantiate()
    _implement(lab)
    lab.profiles.next_script(ChildScript(marker=DONE_MARKER, effects=NO_EFFECTS))
    debrief_id = lab.tick().dispatched
    assert debrief_id is not None
    assert lab.tick().settled == debrief_id

    graded = lab.store.reads.load_activation(debrief_id)
    assert graded.metadata.node == "debrief"
    assert graded.metadata.outcome is Outcome.FAIL_CODE
    assert graded.metadata.evidence is not None
    assert graded.metadata.evidence.claimed_outcome is Outcome.DONE

    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    assert lab.store.reads.load_gate(gate_id).metadata.gate_node == "triage"


# --- findings: derived once, stored on the ledger, rendered from there -------


def _evidence(**values: object) -> Evidence:
    """One close evidence carrier, with only the fields a case is about."""
    return Evidence.model_validate(values)


def test_findings_are_derived_from_the_close_carriers_in_a_fixed_order() -> None:
    """Finding 6: the mapping is stated, deterministic and over existing fields."""
    record = ActivationRecord(
        id="wf-9",
        status="closed",
        metadata=ActivationMetadata.model_validate(
            {
                "wf_root_id": "wf-1",
                "node": "review",
                "round_no": 2,
                "seq": 3,
                "idempotency_key": "k",
                "mint_reason": "edge",
                "crew_profile": "fake",
                "model": "fake",
                "session_id": "s",
                "intended_base_commit": "a" * 40,
                "lifecycle": "closed",
                "outcome": Outcome.REJECT.value,
                "evidence": _evidence(
                    verify=(
                        {
                            "cmd": "ok.sh",
                            "exit_code": 0,
                            "attempts": 1,
                            "script_digest": "0" * 64,
                        },
                        {
                            "cmd": "red.sh",
                            "exit_code": 1,
                            "attempts": 3,
                            "script_digest": "1" * 64,
                        },
                    ),
                    undeclared_effects=("src/stray.py",),
                    claimed_outcome=Outcome.ACCEPT.value,
                    note="BLOCKER: the guard is missing",
                ),
            }
        ),
    )

    rows = findings_of(record)

    assert [(row.severity, row.text) for row in rows] == [
        (Severity.BLOCKER, "verify `red.sh` exited 1 after 3"),
        (Severity.MAJOR, "claimed accept, graded reject"),
        (Severity.MAJOR, "undeclared effect: src/stray.py"),
        (Severity.BLOCKER, "review graded reject: BLOCKER: the guard is missing"),
    ]
    assert {row.round_no for row in rows} == {2}
    assert findings_of(record) == rows


def test_the_ledger_stores_one_rounds_findings_when_it_closes(
    tmp_path: Path,
) -> None:
    """Finding 6: §3.3's `findings` table has a writer, inside the close."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        store = ledger_store(database)
        root = make_root(store, load_definition())
        activation = store.mint_activation(root.root_id, entry_request()).activation
        store.record_dispatch(activation.activation_id, handle())
        store.record_exit(activation.activation_id, EXIT_RECORD)
        closed = store.close_activation(
            activation.activation_id,
            Outcome.FAIL_CODE,
            evidence=_evidence(
                verify=(
                    {
                        "cmd": "red.sh",
                        "exit_code": 2,
                        "attempts": 1,
                        "script_digest": "2" * 64,
                    },
                ),
                claimed_outcome=Outcome.DONE.value,
            ),
        )
        with database.locked() as connection:
            rows = connection.execute(
                "SELECT activation_id, round_no, severity, text FROM findings "
                "ORDER BY rowid"
            ).fetchall()
        # Closing again re-derives rather than duplicating.
        store.close_activation(closed.activation_id, Outcome.FAIL_CODE)
        with database.locked() as connection:
            again = connection.execute("SELECT COUNT(*) FROM findings").fetchone()

    derived = findings_of(closed)
    assert [(row[0], row[1], row[2], row[3]) for row in rows] == [
        (item.activation_id, item.round_no, item.severity.value, item.text)
        for item in derived
    ]
    assert derived
    assert again[0] == len(derived)


# --- the reviewer's OWN findings (finding 6) ---------------------------------

REVIEW_REPORT: Final[str] = (
    "# Review of cr-3411.5\n"
    "\n"
    "1. **BLOCKER** — `workflow_interpreter/ledger/store.py:383`: the close "
    "writes no reviewer row.\n"
    "   The rows are derived from carriers, so the review is lost.\n"
    "2. MAJOR — `workflow_interpreter/bdio/findings.py:74`: the mapping is "
    "documented as derivation.\n"
    "3. the third item names no severity at all.\n"
)
EVIDENCE_TRANSCRIPT: Final[str] = "verify-log.txt"
EVIDENCE_TRANSCRIPT_BODY: Final[str] = (
    "$ pytest -q\n42 passed\n$ ruff check\nAll checks passed\n"
)


def _review_node() -> Node:
    """The shipped graph's `review` node — the one that writes findings."""
    return next(
        node
        for node in load_graph(AUTHORING_FIXTURE).document.node
        if node.name == "review"
    )


def _outputs(
    tmp_path: Path,
    body: str | None,
    name: str = REVIEW_REPORT_FILE,
    beside: Mapping[str, str] | None = None,
) -> tuple[Git, Path, str]:
    """One pinned outputs tree, as the exit pins the reviewer's own.

    `body` is the report; `None` writes no report at all, which is the tree a
    reviewer that recorded only evidence leaves. `beside` is that evidence.
    """
    repo = tmp_path / "review-repo"
    repo.mkdir(exist_ok=True)
    _git(repo, "init", "--quiet", "--initial-branch=main")
    written = dict(beside or {})
    if body is not None:
        written[name] = body
    for path, text in written.items():
        (repo / path).write_text(text, encoding="utf-8")
    _git(repo, "add", "--", *written)
    tree = _git(repo, "write-tree")
    wrapper_root = tmp_path / "review-wrapper"
    wrapper_root.mkdir(exist_ok=True)
    git = Git(InspectorConfig(repo_root=repo, wrapper_root=wrapper_root, host="lab"))
    return git, repo, tree


def test_a_reviews_numbered_findings_are_extracted_unrewritten(tmp_path: Path) -> None:
    """Finding 6: the rows are the REVIEW's text, severity and `file:line`."""
    git, repo, tree = _outputs(tmp_path, REVIEW_REPORT)

    extracted = review_findings(_review_node(), git, repo, tree).findings

    assert [item.severity for item in extracted] == [
        Severity.BLOCKER,
        Severity.MAJOR,
        Severity.MAJOR,
    ]
    assert extracted[0].text.startswith("1. **BLOCKER**")
    assert "ledger/store.py:383" in extracted[0].text
    assert "The rows are derived from carriers" in extracted[0].text
    assert "bdio/findings.py:74" in extracted[1].text
    assert extracted[2].text == "3. the third item names no severity at all."


def test_an_unstructured_review_artifact_is_stored_whole(tmp_path: Path) -> None:
    """A report with no numbering is kept, not dropped and not summarised."""
    git, repo, tree = _outputs(tmp_path, "the guard is missing at store.py:383\n")

    extracted = review_findings(_review_node(), git, repo, tree).findings

    assert [item.text for item in extracted] == ["the guard is missing at store.py:383"]


def test_an_oversized_review_artifact_is_truncated_not_refused(
    tmp_path: Path,
) -> None:
    """Finding 6: the bound is stated in bytes and marked where it bites."""
    body = "".join(
        f"{number}. BLOCKER — {'x' * MAX_FINDING_BYTES}\n" for number in range(1, 20)
    )
    git, repo, tree = _outputs(tmp_path, body)

    extracted = review_findings(_review_node(), git, repo, tree).findings

    assert extracted
    assert all(
        len(item.text.encode("utf-8")) <= MAX_FINDING_BYTES for item in extracted
    )
    total = sum(len(item.text.encode("utf-8")) for item in extracted)
    assert total <= MAX_REVIEW_FINDINGS_BYTES
    assert any(TRUNCATION_MARKER in item.text for item in extracted)


def test_a_blob_too_large_to_read_leaves_a_row_that_says_so(
    tmp_path: Path,
) -> None:
    """A findings file past the reading budget is reported, never refused."""
    git, repo, tree = _outputs(
        tmp_path, "1. BLOCKER — " + "x" * MAX_REVIEW_ARTIFACT_BYTES + "\n"
    )

    extracted = review_findings(_review_node(), git, repo, tree).findings

    assert len(extracted) == 1
    assert REVIEW_REPORT_FILE in extracted[0].text
    assert TRUNCATION_MARKER in extracted[0].text


def test_only_the_named_report_of_the_outputs_tree_is_read(tmp_path: Path) -> None:
    """Finding 6: evidence beside the report is never part of a finding."""
    git, repo, tree = _outputs(
        tmp_path,
        REVIEW_REPORT,
        beside={EVIDENCE_TRANSCRIPT: EVIDENCE_TRANSCRIPT_BODY},
    )

    extracted = review_findings(_review_node(), git, repo, tree).findings

    assert len(extracted) == 3
    assert extracted[-1].text == "3. the third item names no severity at all."
    assert not any("pytest -q" in item.text for item in extracted)


def test_an_evidence_only_tree_is_a_diagnostic_and_not_a_finding(
    tmp_path: Path,
) -> None:
    """Finding 6: a missing report never becomes a MAJOR nobody wrote."""
    git, repo, tree = _outputs(
        tmp_path, None, beside={EVIDENCE_TRANSCRIPT: EVIDENCE_TRANSCRIPT_BODY}
    )

    report = review_findings(_review_node(), git, repo, tree)

    assert report.findings == ()
    assert report.missing is True


def test_the_no_findings_report_yields_no_review_rows(tmp_path: Path) -> None:
    """The declared no-findings report is zero rows, not one row saying so."""
    git, repo, tree = _outputs(tmp_path, f"{REVIEW_NO_FINDINGS}\n")

    report = review_findings(_review_node(), git, repo, tree)

    assert report.findings == ()
    assert report.missing is False


def test_an_absent_report_is_recorded_as_one_diagnostic_row(
    fake_store: WorkflowStore,
) -> None:
    """Finding 6: the close states the report was absent, as INFO, once."""
    _, closed = _closed_review(
        fake_store, Evidence(claimed_outcome=Outcome.REJECT, review_report_missing=True)
    )

    rows = findings_of(closed)

    absent = [
        row
        for row in rows
        if row.text == TEXT_REVIEW_ABSENT.format(file=REVIEW_REPORT_FILE)
    ]
    assert len(absent) == 1
    assert absent[0].kind is FindingKind.DIAGNOSTIC
    assert absent[0].severity is Severity.INFO
    assert not any(row.kind is FindingKind.REVIEW for row in rows)


def test_a_writer_node_contributes_no_review_findings(tmp_path: Path) -> None:
    """Only a node the graph lets REJECT is read for a verdict about others."""
    implement = next(
        node
        for node in load_graph(AUTHORING_FIXTURE).document.node
        if node.name == "implement"
    )

    git, repo, tree = _outputs(tmp_path, REVIEW_REPORT)

    assert review_findings(implement, git, repo, tree).findings == ()


def test_a_real_review_round_puts_its_findings_on_the_record(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Finding 6, end to end: the wrapper reads the artifact the reviewer wrote.

    Nothing here hands the engine a carrier. A `review` child writes its
    numbered findings into `$WF_ARTIFACT_DIR` exactly as the shipped graph
    instructs, and the evidence its close records — the evidence every backend
    is handed — carries them.
    """
    lab = _lab(tmp_path, signing_config, sign_payload)
    lab.instantiate()
    _implement(lab)
    lab.debrief_round()
    lab.profiles.next_script(
        ChildScript(
            marker=REJECT_MARKER,
            effects=NO_EFFECTS,
            artifact_path=REVIEW_REPORT_FILE,
            artifact_body=REVIEW_REPORT,
        )
    )
    review_id = lab.tick().dispatched
    assert review_id is not None
    assert lab.tick().settled == review_id

    activation = lab.store.reads.load_activation(review_id)

    assert activation.metadata.node == "review"
    evidence = activation.metadata.evidence
    assert evidence is not None
    assert [item.severity for item in evidence.review_findings] == [
        Severity.BLOCKER,
        Severity.MAJOR,
        Severity.MAJOR,
    ]
    assert "ledger/store.py:383" in evidence.review_findings[0].text
    rows = [row for row in findings_of(activation) if row.kind is FindingKind.REVIEW]
    assert [row.text for row in rows] == [
        item.text for item in evidence.review_findings
    ]


def _reviewed_evidence(tmp_path: Path) -> Evidence:
    """Close evidence carrying the three findings the reviewer wrote."""
    return Evidence(
        claimed_outcome=Outcome.REJECT,
        review_findings=review_findings(
            _review_node(), *_outputs(tmp_path, REVIEW_REPORT)
        ).findings,
    )


def _closed_review(
    store: WorkflowStore, evidence: Evidence
) -> tuple[RootRecord, ActivationRecord]:
    """One activation minted, dispatched and CLOSED as a rejecting review."""
    root = make_root(store, load_definition())
    activation = store.mint_activation(root.root_id, entry_request()).activation
    store.record_dispatch(activation.activation_id, handle())
    store.record_exit(activation.activation_id, EXIT_RECORD)
    return root, store.close_activation(
        activation.activation_id, Outcome.REJECT, evidence=evidence
    )


def test_the_reviewers_findings_reach_the_bd_backend_unrewritten(
    tmp_path: Path, fake_store: WorkflowStore
) -> None:
    """Finding 6: bd carries the same three findings, on the activation record."""
    evidence = _reviewed_evidence(tmp_path)

    _, closed = _closed_review(fake_store, evidence)

    rows = [row for row in findings_of(closed) if row.kind is FindingKind.REVIEW]
    assert [row.text for row in rows] == [
        item.text for item in evidence.review_findings
    ]
    assert [row.severity for row in rows] == [
        item.severity for item in evidence.review_findings
    ]
    assert findings_of(closed)[: len(rows)] == tuple(rows)


def test_the_reviewers_findings_are_ledger_rows_in_durable_order(
    tmp_path: Path,
) -> None:
    """Finding 6: §3.3's table holds the review's own bytes, review rows first."""
    evidence = _reviewed_evidence(tmp_path)
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _, closed = _closed_review(ledger_store(database), evidence)
        with database.locked() as connection:
            rows = connection.execute(
                "SELECT severity, text, kind FROM findings "
                "WHERE activation_id = ? ORDER BY rowid",
                (closed.activation_id,),
            ).fetchall()

    review = [row for row in rows if row[2] == FindingKind.REVIEW.value]
    assert [row[1] for row in review] == [
        item.text for item in evidence.review_findings
    ]
    assert [row[0] for row in review] == [
        item.severity.value for item in evidence.review_findings
    ]
    assert [row[2] for row in rows[: len(review)]] == [FindingKind.REVIEW.value] * len(
        review
    )
    assert any(row[2] == FindingKind.DIAGNOSTIC.value for row in rows)


def test_the_reviewers_findings_survive_the_export_round_trip(
    tmp_path: Path,
) -> None:
    """Finding 6: the carrier is exported state, so the rows are re-derivable."""
    evidence = _reviewed_evidence(tmp_path)
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _, closed = _closed_review(ledger_store(database), evidence)
        first = write_export(database, TASK).read_bytes()

    import_export(
        export_path(repo_root, TASK),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )

    with open_ledger(repo_root, wrapper_root) as reopened:
        second = write_export(reopened, TASK).read_bytes()
        restored = ledger_store(reopened).reads.load_activation(closed.activation_id)

    assert second == first
    assert findings_of(restored) == findings_of(closed)
    assert [row.text for row in findings_of(restored) if row.kind is FindingKind.REVIEW]


def _findings_rows(database: LedgerDatabase) -> list[tuple[str, int, str, str, str]]:
    """§3.3's durable `findings` table, read straight out of SQL."""
    with database.locked() as connection:
        return [
            (row[0], int(row[1]), row[2], row[3], row[4])
            for row in connection.execute(
                "SELECT activation_id, round_no, severity, text, kind FROM findings "
                "ORDER BY rowid"
            ).fetchall()
        ]


def test_the_import_rebuilds_the_findings_table_from_the_carriers(
    tmp_path: Path,
) -> None:
    """Finding 6: a restored ledger answers §3.3 with the same rows, in order."""
    evidence = _reviewed_evidence(tmp_path)
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _closed_review(ledger_store(database), evidence)
        before = _findings_rows(database)
        write_export(database, TASK)

    import_export(
        export_path(repo_root, TASK),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )

    with open_ledger(repo_root, wrapper_root) as reopened:
        after = _findings_rows(reopened)

    assert any(row[4] == FindingKind.REVIEW.value for row in before)
    assert after == before


def test_findings_md_shows_the_reviewers_findings_first(tmp_path: Path) -> None:
    """Finding 6: `findings.md` is the review, before the engine's diagnostics."""
    evidence = _reviewed_evidence(tmp_path)
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        store = ledger_store(database)
        root, closed = _closed_review(store, evidence)
        rendered = render_run(
            root, (closed,), store.reads.list_gates(root.root_id), round_no=1
        )

    positions = [
        rendered.findings_md.find(item.text) for item in evidence.review_findings
    ]
    assert all(position > 0 for position in positions), rendered.findings_md
    assert positions == sorted(positions)
    diagnostic = next(
        row for row in findings_of(closed) if row.kind is FindingKind.DIAGNOSTIC
    )
    assert rendered.findings_md.find(diagnostic.text) > positions[-1]


def test_the_render_shows_each_rounds_findings_in_record_order(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Finding 6: `findings.md` is those rows, not a paraphrase of the outcome."""
    lab = _lab(tmp_path, signing_config, sign_payload)
    lab.pin_checks(
        {
            "scripts/verify-feature.sh": FAILING,
            "scripts/review-checks.sh": PASSING,
            "scripts/verify-debrief.sh": PASSING,
        }
    )
    root = lab.instantiate()
    _implement(lab)
    activations = lab.store.reads.list_activations(root.root_id)

    rendered = render_run(
        root, activations, lab.store.reads.list_gates(root.root_id), round_no=1
    )

    expected = [
        finding
        for activation in sorted(activations, key=lambda item: int(item.metadata.seq))
        for finding in findings_of(activation)
    ]
    assert expected
    positions = [
        rendered.findings_md.find(f"{item.severity.value.upper()}: {item.text}")
        for item in expected
    ]
    assert all(position >= 0 for position in positions), rendered.findings_md
    assert positions == sorted(positions)


# --- terminal cleanup, and the liveness it waits on (§3.9) -------------------


def _live_receipt(lab: ForemanLab, activation_id: str) -> Path:
    """A launch receipt whose handle names a process that IS running.

    The test process itself, which is the only pid a test can claim is alive
    without racing a child: `prove_liveness` answers ALIVE only when pid, boot
    id and start time all agree, so a fabricated handle would prove nothing.
    """
    config = lab.inspector_config
    pid = os.getpid()
    handle = ProcessHandle(
        pid=pid,
        pgid=os.getpgid(pid),
        host=config.host,
        host_boot_id=read_boot_id(config) or "",
        proc_start_time=read_start_time(config, pid) or "",
        started_at="2026-09-17T00:00:00Z",
        log_path=str(lab.wiring().paths.activation_dir(activation_id) / "raw.log"),
        session_id="live",
    )
    path = lab.wiring().paths.receipt(activation_id)
    write_record(
        path,
        LaunchReceipt(
            launch_id="still-running",
            root_id=lab.root.root_id if lab.root is not None else "",
            activation_id=activation_id,
            argv=("/bin/sleep",),
            cwd=str(lab.repo),
            handle=handle,
        ),
    )
    return path


def test_terminal_cleanup_defers_all_three_while_a_crew_may_be_alive(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Finding 5: durable close is a record event, process death is not (§3.9).

    The root settles while one activation's receipt still names a running
    process. Worktree, verify tree and scratch are ONE decision, so all three
    survive that tick; once the receipt no longer names a live process the next
    tick takes all three.
    """
    lab = ForemanLab(
        tmp_path,
        overrides={"region.build-review.max_entries": 1},
        signing=signing_config,
        signer=sign_payload,
    )
    lab.instantiate()
    _implement(lab)
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"reject"}\n',
            effects=NO_EFFECTS,
            artifact_path="review.md",
            artifact_body="rework this",
        )
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review
    exhaustion = lab.tick().opened_gate
    assert exhaustion is not None
    lab.approve(exhaustion, Outcome.ABANDON)
    assert lab.tick().closed_gates == (exhaustion,)

    wiring = lab.wiring()
    verify_tree = wiring.paths.verify_tree
    verify_tree.mkdir(parents=True, exist_ok=True)
    (verify_tree / "left-behind").write_text("a killed check's checkout\n")
    scratch = wiring.paths.scratch(review)
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "tmpfile").write_text("the crew's working bytes\n")
    receipt = _live_receipt(lab, review)

    assert lab.tick().terminal is True

    assert wiring.paths.worktree.exists()
    assert verify_tree.exists()
    assert scratch.exists()

    receipt.unlink()
    lab.tick()

    assert not wiring.paths.worktree.exists()
    assert not verify_tree.exists()
    assert not scratch.exists()


# --- re-verification from the export alone (§3.6, D21) -----------------------


@pytest.fixture
def exported_task(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> Iterator[tuple[Path, Path]]:
    """One signed, closed gate exported to `.wf/export/<task>.jsonl`.

    Yields the export file and the repository root, with the ledger CLOSED so
    a test may delete the database and still hold the whole record.
    """
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        store = ledger_store(
            database, verifier=GateVerifier(signing_config, database.repo_root)
        )
        root_id, gate_id = _open_gate(store)
        gate = store.reads.load_gate(gate_id)
        close(store, root_id, gate, approval_payload(root_id, gate), sign_payload)
        path = write_export(database, TASK)
    yield path, repo_root


@pytest.fixture
def other_exported_task(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> Path:
    """A SECOND task's export, signed by the same key, in its own repository.

    The same key deliberately: an approval transplanted out of this file must
    be refused for the gate it approved, not for who signed it.
    """
    repo_root, wrapper_root = repository(tmp_path / "elsewhere")
    with open_ledger(repo_root, wrapper_root) as database:
        store = ledger_store(
            database,
            OTHER_TASK,
            verifier=GateVerifier(signing_config, database.repo_root),
        )
        root_id, gate_id = _open_gate(store)
        gate = store.reads.load_gate(gate_id)
        close(store, root_id, gate, approval_payload(root_id, gate), sign_payload)
        return write_export(database, OTHER_TASK)


def test_an_approval_re_verifies_from_the_export_alone(
    exported_task: tuple[Path, Path],
) -> None:
    """D21: the export carries the trust, so no allow-list is needed to check it."""
    path, _ = exported_task
    stored = read_signatures(path)

    assert stored
    results = tuple(verify_signature(item) for item in stored)

    assert all(result.verified for result in results), [
        result.reason for result in results
    ]


def test_a_tampered_signature_is_refused(exported_task: tuple[Path, Path]) -> None:
    """One flipped byte and the approval stops being one."""
    path, _ = exported_task
    stored = read_signatures(path)[0]
    # In the MIDDLE of the armored blob: the tail of an sshsig is framing and
    # padding, where a flipped byte is not a changed signature.
    signature = bytearray(stored.signature_bytes)
    position = next(
        index
        for index in range(len(signature) // 2, len(signature))
        if chr(signature[index]).isalnum()
    )
    signature[position] = ord("A") if chr(signature[position]) != "A" else ord("B")

    result = verify_signature(
        stored.model_copy(update={"signature_bytes": bytes(signature)})
    )

    assert not result.verified
    assert result.reason is not None


def test_the_export_is_enough_without_the_ledger_or_the_wrapper_root(
    tmp_path: Path, exported_task: tuple[Path, Path]
) -> None:
    """The acceptance: a fresh clone, `ledger.db` and the wrapper root gone.

    The BYTES half of D21. Provenance is anchored outside the export and is
    tested above; what this pins is that nothing about the signature check
    needs the database, the wrapper root or today's allow-list.
    """
    path, repo_root = exported_task
    clone = tmp_path / "fresh-clone"
    clone.mkdir()
    copied = clone / path.name
    shutil.copyfile(path, copied)
    ledger_path(repo_root).unlink()
    shutil.rmtree(tmp_path / "wrapper", ignore_errors=True)
    shutil.rmtree(repo_root)

    results = tuple(verify_signature(item) for item in read_signatures(copied))

    assert results
    assert all(result.verified for result in results)


# --- the anchors re-verification may not take from the export (finding 2) ----


def _anchor_repo(tmp_path: Path, export: Path, *, pin: bool = True) -> Path:
    """A repository with NO history, holding the export under its close ref.

    The secondary anchor of §3.6: `refs/wf/exports/<task>` as the close wrote
    it, in a repository whose HEAD carries nothing — so these cases exercise
    the fallback, and the fresh-clone family below exercises the primary
    anchor, the export the landed history carries.
    """
    repo = tmp_path / "anchor-repo"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch=main")
    _git(repo, "config", "user.email", "wf@test")
    _git(repo, "config", "user.name", "wf test")
    target = repo / ".wf" / "export" / export.name
    target.parent.mkdir(parents=True)
    shutil.copyfile(export, target)
    if pin:
        _pin_export(repo, target)
    return repo


def _pin_export(repo: Path, target: Path) -> str:
    """Pin the export bytes exactly as the closing merge does (§3.6, journal)."""
    oid = _git(repo, "hash-object", "-w", "--no-filters", "--", str(target))
    _git(repo, "update-ref", EXPORT_REF_TEMPLATE.format(task_id=TASK), oid)
    return oid


def _anchor(repo: Path, signing: SigningConfig) -> TrustAnchor:
    """The operator's two anchors: this clone and their own allow-list."""
    return TrustAnchor(repo_root=repo, allowed_signers=signing.allowed_signers_path)


def _export_path(repo: Path) -> Path:
    """Where the export lives inside the anchor clone."""
    return repo / ".wf" / "export" / f"{TASK}{EXPORT_SUFFIX}"


def _rewrite_signature_row(path: Path, updates: dict[str, object]) -> None:
    """Rewrite the one `signatures` row of an export, as a tamperer would."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for raw in lines:
        line = json.loads(raw) if raw.strip() else None
        if (
            isinstance(line, dict)
            and line.get(ExportKey.TABLE.value) == LedgerTable.SIGNATURES.value
        ):
            line[ExportKey.ROW.value] = {**line[ExportKey.ROW.value], **updates}
            raw = json.dumps(line)
        out.append(raw)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def test_an_anchored_export_reports_all_four_answers(
    tmp_path: Path, exported_task: tuple[Path, Path], signing_config: SigningConfig
) -> None:
    """The good case on the fallback anchor: all four answers, from the ref."""
    path, _ = exported_task
    repo = _anchor_repo(tmp_path, path)

    verdict = verify_export(_export_path(repo), TASK, _anchor(repo, signing_config))

    assert verdict.accepted
    assert (verdict.bytes_valid, verdict.export_pinned) == (True, True)
    assert (verdict.signer_trusted, verdict.entry_unchanged) == (True, True)
    assert verdict.blob_oid == verdict.pinned_oid
    assert verdict.anchor is ExportAnchor.REF


def test_an_export_that_is_not_the_pinned_blob_is_refused(
    tmp_path: Path, exported_task: tuple[Path, Path], signing_config: SigningConfig
) -> None:
    """Finding 2: the bytes must be the ones the close recorded (§3.6)."""
    path, _ = exported_task
    repo = _anchor_repo(tmp_path, path)
    target = _export_path(repo)
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    verdict = verify_export(target, TASK, _anchor(repo, signing_config))

    assert verdict.bytes_valid
    assert not verdict.export_pinned
    assert not verdict.accepted
    assert verdict.blob_oid != verdict.pinned_oid


def test_an_unpinned_export_is_refused(
    tmp_path: Path, exported_task: tuple[Path, Path], signing_config: SigningConfig
) -> None:
    """An export neither history nor a ref names is one no close recorded."""
    path, _ = exported_task
    repo = _anchor_repo(tmp_path, path, pin=False)

    verdict = verify_export(_export_path(repo), TASK, _anchor(repo, signing_config))

    assert not verdict.export_pinned
    assert not verdict.accepted
    assert verdict.anchor is None
    assert any("nothing anchors this export" in reason for reason in verdict.reasons)


def test_a_tampered_payload_is_refused(
    tmp_path: Path, exported_task: tuple[Path, Path], signing_config: SigningConfig
) -> None:
    """A changed payload is not the payload anybody signed."""
    path, _ = exported_task
    repo = _anchor_repo(tmp_path, path)
    target = _export_path(repo)
    stored = read_signatures(target)[0]
    _rewrite_signature_row(
        target,
        {
            "payload_bytes": {
                "base64": base64.b64encode(stored.payload_bytes + b" ").decode()
            }
        },
    )
    _pin_export(repo, target)

    verdict = verify_export(target, TASK, _anchor(repo, signing_config))

    assert not verdict.bytes_valid
    assert not verdict.accepted


def test_a_self_signed_replacement_key_fails_the_anchor(
    tmp_path: Path,
    exported_task: tuple[Path, Path],
    signing_config: SigningConfig,
    sign_payload: Signer,
) -> None:
    """Finding 2: an export cannot certify its own signer.

    The tamperer mints a key, re-signs the recorded payload with it, replaces
    the fingerprint and the stored allow-list entry, and re-pins the bytes — so
    the export is internally consistent and git agrees it is the file it names.
    Only the trust root, which is not in the export, can refuse it.
    """
    path, _ = exported_task
    repo = _anchor_repo(tmp_path, path)
    target = _export_path(repo)
    _forge_signer(target, tmp_path, sign_payload)
    _pin_export(repo, target)

    verdict = verify_export(target, TASK, _anchor(repo, signing_config))

    # The export vouches for itself perfectly — the bytes-only half of D21,
    # which is what S4 shipped before this fix, accepts the forgery outright —
    # and git agrees these are the bytes it holds. Neither is provenance.
    assert all(result.verified for result in verify_approvals(target))
    assert verdict.bytes_valid
    assert verdict.export_pinned
    assert not verdict.signer_trusted
    assert not verdict.accepted
    assert any("trust root" in reason for reason in verdict.reasons)


def test_a_transplanted_approval_is_not_an_approval_of_this_task(
    tmp_path: Path,
    exported_task: tuple[Path, Path],
    other_exported_task: Path,
    signing_config: SigningConfig,
) -> None:
    """An approval is bound to the gate rows its OWN export carries (§3.6).

    The tamperer copies a valid `signatures` row out of another task's export
    and pins the result: every byte verifies, the blob is the one git names and
    the signer is on the trust root — so nothing but the binding check can see
    that the extra approval closed somebody else's gate.
    """
    path, _ = exported_task
    repo = _anchor_repo(tmp_path, path)
    target = _export_path(repo)
    foreign = [
        line
        for line in other_exported_task.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get(ExportKey.TABLE.value) == LedgerTable.SIGNATURES.value
    ]
    assert len(foreign) == 1
    target.write_text(
        "\n".join([*target.read_text(encoding="utf-8").splitlines(), *foreign]) + "\n",
        encoding="utf-8",
    )
    _pin_export(repo, target)

    verdict = verify_export(target, TASK, _anchor(repo, signing_config))

    assert (verdict.export_pinned, verdict.signer_trusted) == (True, True)
    refused = [result for result in verdict.approvals if not result.verified]
    assert len(refused) == len(verdict.approvals) - 1
    assert refused[0].reason is not None
    assert f"not an approval of a gate of task {TASK}" in refused[0].reason
    assert refused[0].reason in verdict.reasons
    assert not verdict.bytes_valid
    assert not verdict.accepted


def test_another_tasks_export_at_this_path_lends_this_task_no_approval(
    tmp_path: Path,
    exported_task: tuple[Path, Path],
    other_exported_task: Path,
    signing_config: SigningConfig,
) -> None:
    """The whole file swapped: valid, pinned, trusted — and not this task's.

    Without the binding check every other answer is yes, and the other task's
    approvals are reported as approvals of this one.
    """
    path, _ = exported_task
    repo = _anchor_repo(tmp_path, path)
    target = _export_path(repo)
    target.write_bytes(other_exported_task.read_bytes())
    _pin_export(repo, target)

    verdict = verify_export(target, TASK, _anchor(repo, signing_config))

    assert (verdict.export_pinned, verdict.signer_trusted) == (True, True)
    assert all(not result.verified for result in verdict.approvals)
    assert any(f"belongs to task {OTHER_TASK}" in reason for reason in verdict.reasons)
    assert not verdict.accepted


# --- the acceptance: the real CLI, in a real fresh clone (finding 9) ---------


def _forge_signer(target: Path, tmp_path: Path, sign_payload: Signer) -> None:
    """Mint a key, re-sign the recorded payload and replace the stored entry.

    The tamperer's whole move: after it the export is internally consistent —
    it carries a key, a signature over its own bytes and the allow-list entry
    that certifies them — so only a trust root outside the file can refuse it.
    """
    stored = read_signatures(target)[0]
    forged_key = tmp_path / "forged_key"
    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "attacker",
            "-f",
            str(forged_key),
        ],
        check=True,
        capture_output=True,
        timeout=SCRIPT_TIMEOUT_S,
    )
    public = forged_key.with_suffix(".pub").read_text(encoding="utf-8").split()
    blob = base64.b64decode(public[1], validate=True)
    entry = stored.signer.model_copy(
        update={
            "key_type": public[0],
            "key_blob": public[1],
            "fingerprint": key_fingerprint(blob),
        }
    )
    _rewrite_signature_row(
        target,
        {
            "signature_bytes": {
                "base64": base64.b64encode(
                    sign_payload(stored.payload_bytes, forged_key)
                ).decode()
            },
            "signer_fingerprint": key_fingerprint(blob),
            "allowed_signers_entry": entry.model_dump_json(),
        },
    )


def _commit_all(repo: Path, message: str) -> None:
    """Commit the export exactly as §3.6's step 20 says the orchestrator does."""
    _git(repo, "add", "--", str(Path(".wf") / "export"))
    _git(repo, "commit", "--quiet", "-m", message)


@pytest.fixture
def landed_export(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> Path:
    """A repository whose HISTORY carries one closed task's export (§3.6).

    The real close path writes it — the gate is signed and closed through the
    store, and the close exports the task — and then the orchestrator commits
    `.wf/export/<task>.jsonl` beside the landed work, which is the step that
    puts these bytes on the history a clone transports. `.wf/ledger.db` is
    never added, so the clone cannot have one.
    """
    repo_root = tmp_path / "origin"
    repo_root.mkdir()
    _git(repo_root, "init", "--quiet", "--initial-branch=main")
    _git(repo_root, "config", "user.email", "wf@test")
    _git(repo_root, "config", "user.name", "wf test")
    (repo_root / "README.md").write_text("origin\n", encoding="utf-8")
    _git(repo_root, "add", "--", "README.md")
    _git(repo_root, "commit", "--quiet", "-m", "base")
    wrapper_root = tmp_path / "wrapper"
    wrapper_root.mkdir(exist_ok=True)
    with open_ledger(repo_root, wrapper_root) as database:
        store = ledger_store(
            database, verifier=GateVerifier(signing_config, database.repo_root)
        )
        root_id, gate_id = _open_gate(store)
        gate = store.reads.load_gate(gate_id)
        close(store, root_id, gate, approval_payload(root_id, gate), sign_payload)
        write_export(database, TASK)
    _commit_all(repo_root, "land: the task and its export")
    return repo_root


def _fresh_clone(tmp_path: Path, origin: Path, name: str = "fresh-clone") -> Path:
    """A plain `git clone`: no ledger, no wrapper root, no custom refs."""
    clone = tmp_path / name
    _git(tmp_path, "clone", "--quiet", str(origin), str(clone))
    assert not (clone / ".wf" / "ledger.db").exists()
    assert not _git(clone, "for-each-ref", "refs/wf")
    return clone


def _cli_verify(clone: Path, signing: SigningConfig, tmp_path: Path) -> tuple[int, str]:
    """Run the real `wf ledger verify` in `clone`, as an operator would."""
    config = tmp_path / f"{clone.name}.toml"
    home = tmp_path / "no-home"
    wrapper_root = wrapper_root_for(home, clone)
    config.write_text(
        f'''repo_root = "{clone}"
wrapper_home = "{home}"
host = "host"
actor = "actor"

[tracker.bd]
workspace = "{tmp_path / "no-bd"}"
actor = "actor"

[inspector]
repo_root = "{clone}"
wrapper_root = "{wrapper_root}"
host = "host"
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "workflow_interpreter.ledger",
            "--config",
            str(config),
            "verify",
            TASK,
            "--allowed-signers",
            str(signing.allowed_signers_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        check=False,
        timeout=SCRIPT_TIMEOUT_S,
    )
    return completed.returncode, completed.stdout.decode() + completed.stderr.decode()


def test_the_cli_verifies_a_task_in_a_real_fresh_clone(
    tmp_path: Path, landed_export: Path, signing_config: SigningConfig
) -> None:
    """The §6 acceptance, end to end: `git clone`, then the actual command.

    Nothing is manufactured here. The anchor is the export blob the landed
    commit carries, which is why a clone that fetched no `refs/wf/*` can still
    answer all four questions.
    """
    clone = _fresh_clone(tmp_path, landed_export)

    code, output = _cli_verify(clone, signing_config, tmp_path)

    assert code == 0, output
    assert "bytes valid: yes" in output, output
    assert f"export pinned: yes ({ExportAnchor.COMMITTED.value})" in output, output
    assert "signer trusted: yes" in output, output
    assert "historical entry unchanged: yes" in output, output


def test_the_cli_refuses_export_bytes_altered_after_the_commit(
    tmp_path: Path, landed_export: Path, signing_config: SigningConfig
) -> None:
    """Finding 9: the anchor is the COMMITTED blob, not the file on disk."""
    clone = _fresh_clone(tmp_path, landed_export)
    target = _export_path(clone)
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    code, output = _cli_verify(clone, signing_config, tmp_path)

    assert code != 0, output
    assert "export pinned: no" in output, output


def test_the_cli_refuses_a_self_signed_replacement_key_in_the_clone(
    tmp_path: Path,
    landed_export: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
) -> None:
    """Finding 9: a forgery committed into history is still not provenance.

    The tamperer owns the clone, so it re-signs the export with its own key AND
    commits it — the bytes anchor now agrees. Only the operator's trust root,
    which is not in the repository at all, refuses it.
    """
    clone = _fresh_clone(tmp_path, landed_export)
    _git(clone, "config", "user.email", "attacker@test")
    _git(clone, "config", "user.name", "attacker")
    _forge_signer(_export_path(clone), tmp_path, sign_payload)
    _commit_all(clone, "land: the export, resigned")

    code, output = _cli_verify(clone, signing_config, tmp_path)

    assert code != 0, output
    assert "bytes valid: yes" in output, output
    assert f"export pinned: yes ({ExportAnchor.COMMITTED.value})" in output, output
    assert "signer trusted: no" in output, output


# --- archive (§3.9, D19) -----------------------------------------------------


def _settled_root(database: LedgerDatabase, task_id: str, root_id: str) -> None:
    """A settled ledger root row, written directly: archive only READS it."""
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO roots (root_id, task_id, seq, attempt, "
            "instance_key, terminal, status, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (root_id, task_id, 1, 1, root_id, "shipped", "closed", "{}"),
        )


def _archive_fixture(tmp_path: Path) -> tuple[Path, Path, Git, str, str]:
    """A repository with one pinned root ref and one run folder to lose."""
    repo = make_repo(tmp_path)
    wrapper_root = tmp_path / "wrapper"
    wrapper_root.mkdir()
    root_id = f"{TASK_ID}-a1"
    ref = f"refs/wf/{root_id}/artifact/one"
    _git(repo, "update-ref", ref, _git(repo, "rev-parse", "HEAD"))
    folder = wrapper_root / root_id
    (folder / "worktree").mkdir(parents=True)
    (folder / "worktree" / "big").write_text("scratch\n", encoding="utf-8")
    git = Git(InspectorConfig(repo_root=repo, wrapper_root=wrapper_root, host="lab"))
    return repo, wrapper_root, git, root_id, ref


def test_archive_refuses_a_task_that_is_not_retired_and_deletes_nothing(
    tmp_path: Path,
) -> None:
    """A task that neither derives `closed()` nor was abandoned keeps its bytes."""
    repo, wrapper_root, git, root_id, ref = _archive_fixture(tmp_path)
    bundle = tmp_path / "bundles" / f"{TASK_ID}.bundle"
    with open_ledger(repo, wrapper_root) as database:
        ensure_task(database, TASK_ID, EPIC_ID)
        _settled_root(database, TASK_ID, root_id)

        with pytest.raises(LedgerExportError, match="not retired"):
            archive_task(
                git,
                database,
                TASK_ID,
                bundle=bundle,
                repo_root=repo,
                wrapper_root=wrapper_root,
            )

    assert (wrapper_root / root_id).is_dir()
    assert _git(repo, "rev-parse", "--verify", ref)
    assert not bundle.exists()


def test_archive_deletes_only_behind_a_bundle_git_accepts(tmp_path: Path) -> None:
    """D19: the refs go only after the bundle verifies, and it restores them."""
    repo, wrapper_root, git, root_id, ref = _archive_fixture(tmp_path)
    bundle = tmp_path / "bundles" / f"{TASK_ID}.bundle"
    with open_ledger(repo, wrapper_root) as database:
        ensure_task(database, TASK_ID, EPIC_ID)
        _settled_root(database, TASK_ID, root_id)
        # A closed task is LANDED and latched: the latch alone is not
        # closure, and `closed()` asks the state first (§3.5) — which since S4
        # is carried by the task's record, so it has to have one.
        seed_contractor_record(database, TASK_ID, epic_id=EPIC_ID)
        record_task_state(database, TASK_ID, TaskState.LANDED)
        record_export_oid(database, TASK_ID, "0" * 40)

        result = archive_task(
            git,
            database,
            TASK_ID,
            bundle=bundle,
            repo_root=repo,
            wrapper_root=wrapper_root,
        )

    assert result.refs == (ref,)
    assert result.run_folders == (wrapper_root / root_id,)
    assert not (wrapper_root / root_id).exists()
    assert bundle.is_file()
    with pytest.raises(subprocess.CalledProcessError):
        _git(repo, "rev-parse", "--verify", ref)
    assert (
        ref
        in subprocess.check_output(
            ["git", "ls-remote", str(bundle)], timeout=GIT_TIMEOUT_S
        ).decode()
    )


def test_archive_refuses_a_bundle_inside_the_repository(tmp_path: Path) -> None:
    """The bundle is what survives the deletion; inside the repo it may not."""
    repo, wrapper_root, git, root_id, _ = _archive_fixture(tmp_path)
    with open_ledger(repo, wrapper_root) as database:
        ensure_task(database, TASK_ID, EPIC_ID)
        _settled_root(database, TASK_ID, root_id)
        # A closed task is LANDED and latched: the latch alone is not
        # closure, and `closed()` asks the state first (§3.5) — which since S4
        # is carried by the task's record, so it has to have one.
        seed_contractor_record(database, TASK_ID, epic_id=EPIC_ID)
        record_task_state(database, TASK_ID, TaskState.LANDED)
        record_export_oid(database, TASK_ID, "0" * 40)

        with pytest.raises(LedgerExportError, match="inside the repository"):
            archive_task(
                git,
                database,
                TASK_ID,
                bundle=repo / "inside.bundle",
                repo_root=repo,
                wrapper_root=wrapper_root,
            )

    assert (wrapper_root / root_id).is_dir()
