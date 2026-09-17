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

import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest

from tests._foreman import LAB_ATTEMPT, LAB_TASK, ForemanLab
from tests._gates import approval_payload, close
from tests._helpers import AUTHORING_FIXTURE
from tests._ledger import TASK, ledger_store, repository
from tests._supervisor import ChildScript, make_repo
from tests.conftest import Signer
from tests.test_ledger_writes import _open_gate
from workflow_interpreter import load_graph
from workflow_interpreter.bdio import GateVerifier, Outcome, SigningConfig
from workflow_interpreter.bdio.carriers import LEDGER_RENDER_REF
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contracts.run_identity import epic_segment
from workflow_interpreter.foreman.ledger_render import (
    EVIDENCE_FILE,
    FINDINGS_FILE,
    render_run,
)
from workflow_interpreter.ledger.archive import archive_task
from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.export import write_export
from workflow_interpreter.ledger.paths import ledger_path
from workflow_interpreter.ledger.reverify import read_signatures, verify_signature
from workflow_interpreter.ledger.tasks import pin_task_backend, record_export_oid
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.verify import (
    ATTEMPT_ENV,
    BASE_COMMIT_ENV,
    EPIC_SEGMENT_ENV,
    TASK_ID_ENV,
)

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
ATTEMPT: Final[int] = 1
DEBRIEF_MAX_BYTES: Final[int] = 16384
PASSING: Final[str] = "#!/bin/sh\nexit 0\n"
FAILING: Final[str] = "#!/bin/sh\nexit 1\n"
DONE_MARKER: Final[str] = '{"outcome":"done"}\n'
NO_DIFF_MARKER: Final[str] = '{"outcome":"no_diff"}\n'
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
    return (
        repo
        / "docs"
        / "workstreams"
        / epic_segment(task_id)
        / "runs"
        / task_id
        / f"a{attempt}"
    )


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


def _run_debrief_check(
    repo: Path, base: str, *, task_id: str = TASK_ID, attempt: str = str(ATTEMPT)
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
            EPIC_SEGMENT_ENV: epic_segment(task_id),
            TASK_ID_ENV: task_id,
            ATTEMPT_ENV: attempt,
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
    """The acceptance: a fresh clone, `ledger.db` and the wrapper root gone."""
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


# --- archive (§3.9, D19) -----------------------------------------------------


def _settled_root(database: LedgerDatabase, task_id: str, root_id: str) -> None:
    """A settled ledger root row, written directly: archive only READS it."""
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO roots (root_id, task_id, seq, attempt, backend, "
            "instance_key, terminal, status, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (root_id, task_id, 1, 1, "ledger", root_id, "shipped", "closed", "{}"),
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
    git = Git(SupervisorConfig(repo_root=repo, wrapper_root=wrapper_root, host="lab"))
    return repo, wrapper_root, git, root_id, ref


def test_archive_refuses_an_unexported_task_and_deletes_nothing(
    tmp_path: Path,
) -> None:
    """No export_oid means the task never closed, and nothing may be retired."""
    repo, wrapper_root, git, root_id, ref = _archive_fixture(tmp_path)
    bundle = tmp_path / "bundles" / f"{TASK_ID}.bundle"
    with open_ledger(repo, wrapper_root) as database:
        pin_task_backend(database, TASK_ID, BackendKind.LEDGER)
        _settled_root(database, TASK_ID, root_id)

        with pytest.raises(LedgerExportError, match="export_oid"):
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
        pin_task_backend(database, TASK_ID, BackendKind.LEDGER)
        _settled_root(database, TASK_ID, root_id)
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
        pin_task_backend(database, TASK_ID, BackendKind.LEDGER)
        _settled_root(database, TASK_ID, root_id)
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
