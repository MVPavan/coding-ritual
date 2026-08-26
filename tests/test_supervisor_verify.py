"""§7.3 check execution: one resolution, an isolated tree, no escaping errors.

Unit-level on purpose. Two of these are about what `subprocess` does with a
RELATIVE program and a working directory, and one is about what happens when
the program cannot be executed at all — none of which a git fixture makes
clearer, and all of which a stubbed `subprocess` would hide completely.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from tests._bdio import load_definition
from tests._supervisor import (
    IMPLEMENT,
    commit_all,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_repo,
    make_store,
    node_of,
)
from workflow_interpreter.schema.models import Node, NodeKind, VerifyCheck
from workflow_interpreter.supervisor import (
    VerifyTreeError,
    pin_verifier_digests,
    pinned_verifier_digests,
    run_checks,
    verifier_digest_key,
)
from workflow_interpreter.supervisor import verify as verify_module
from workflow_interpreter.supervisor.channels import sha256_file
from workflow_interpreter.supervisor.verify import REFUSED_EXIT_CODE, VerifyTree

PROGRAM = "scripts/check.sh"
WITNESS = "evil-ran"
HONEST = "#!/bin/sh\nexit 0\n"
ESCAPE_CWD = "../outside"


def _node(*extra: object, **check: object) -> Node:
    """An `implement` node declaring one check, plus any extra `VerifyCheck`s."""
    checks = (
        VerifyCheck.model_validate({"cmd": PROGRAM, "timeout": "10s"} | check),
        *(entry for entry in extra if isinstance(entry, VerifyCheck)),
    )
    return Node(name=IMPLEMENT, kind=NodeKind.TASK, verify=checks)


def _pins(program: Path, cwd: str | None = None) -> dict[str, str]:
    """The §7.3 pin for `PROGRAM` under `cwd`, taken from `program`'s bytes."""
    return {verifier_digest_key(IMPLEMENT, cwd, PROGRAM): sha256_file(program) or ""}


def _script(path: Path, body: str, *, executable: bool = True) -> Path:
    """Write an `sh` script, executable unless the test says otherwise."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)
    return path


def test_a_check_cwd_cannot_swap_the_program_that_was_hashed(tmp_path: Path) -> None:
    """B4: the file hashed and the file executed are ONE resolved path.

    The probed counterexample: the digest was taken at `tree/argv[0]` while
    `subprocess` resolved the same relative `argv[0]` against `check.cwd`, so a
    runner that put a second script under the declared `cwd` had its own code
    run while the honest script was the one vouched for.
    """
    honest = _script(tmp_path / PROGRAM, HONEST)
    witness = tmp_path / WITNESS
    _script(tmp_path / "sub" / PROGRAM, f"#!/bin/sh\ntouch {witness}\nexit 0\n")

    results = run_checks(_node(cwd="sub"), tmp_path, _pins(honest))

    assert not witness.exists()
    assert results[0].provenance_ok is False
    assert results[0].exit_code == REFUSED_EXIT_CODE
    assert results[0].program == str(tmp_path / "sub" / PROGRAM)


def test_a_check_cwd_still_runs_the_program_it_vouched_for(tmp_path: Path) -> None:
    """B4, the other side: pin the resolved file and the check runs normally."""
    _script(tmp_path / PROGRAM, "#!/bin/sh\nexit 3\n")
    under_cwd = _script(tmp_path / "sub" / PROGRAM, "#!/bin/sh\nexit 0\n")

    results = run_checks(_node(cwd="sub"), tmp_path, _pins(under_cwd, "sub"))

    assert results[0].provenance_ok is True
    assert results[0].exit_code == 0


def test_two_checks_sharing_a_program_name_get_separate_pins(tmp_path: Path) -> None:
    """Sol#27: the pin key was the program name, which is not a key.

    Two legitimate checks on one node can name `scripts/check.sh` under
    different `cwd`s — different files, different digests. The producer wrote
    one key and overwrote the other, so one of the two checks failed provenance
    forever and was never run again.
    """
    here = _script(tmp_path / PROGRAM, HONEST)
    there = _script(tmp_path / "sub" / PROGRAM, "#!/bin/sh\nexit 0\n# different\n")
    node = _node(
        VerifyCheck.model_validate({"cmd": PROGRAM, "timeout": "10s", "cwd": "sub"})
    )
    pins = {**_pins(here), **_pins(there, "sub")}

    results = run_checks(node, tmp_path, pins)

    assert len(pins) == 2
    assert [result.provenance_ok for result in results] == [True, True]
    assert [result.exit_code for result in results] == [0, 0]
    assert results[0].script_digest != results[1].script_digest


def test_a_check_cannot_reach_outside_the_verify_tree(tmp_path: Path) -> None:
    """Sol#1: `cwd` is a RelativePath, and `../` is a relative path.

    A check whose `cwd` climbs out of the detached checkout runs against
    whatever is there — the live working tree the runner may still be writing,
    which is precisely what B1's isolated checkout exists to prevent. Refused
    as a verdict rather than raised, so §7 still produces an exit record.
    """
    tree = tmp_path / "tree"
    tree.mkdir()
    witness = tmp_path / WITNESS
    _script(tmp_path / ESCAPE_CWD / PROGRAM, f"#!/bin/sh\ntouch {witness}\nexit 0\n")

    results = run_checks(
        _node(cwd=ESCAPE_CWD), tree, _pins(tmp_path / ESCAPE_CWD / PROGRAM)
    )

    assert not witness.exists()
    assert results[0].provenance_ok is False
    assert results[0].exit_code == REFUSED_EXIT_CODE
    assert results[0].error is not None
    assert "outside" in results[0].error


def test_a_symlinked_program_cannot_smuggle_the_check_out_of_the_tree(
    tmp_path: Path,
) -> None:
    """Sol#1, the committable version: a repo can carry the escape as a SYMLINK.

    `..` in `cwd` is visible in the pinned graph; a symlink is a file in the
    artifact commit, so it survives `VerifyTree`'s clean-checkout assertion and
    resolves at exec time. Containment is therefore decided after `realpath`,
    not on the spelling of the path.
    """
    tree = tmp_path / "tree"
    (tree / "scripts").mkdir(parents=True)
    witness = tmp_path / WITNESS
    outside = _script(tmp_path / "outside.sh", f"#!/bin/sh\ntouch {witness}\nexit 0\n")
    (tree / PROGRAM).symlink_to(outside)

    results = run_checks(_node(), tree, _pins(outside))

    assert not witness.exists()
    assert results[0].provenance_ok is False
    assert results[0].error is not None
    assert "outside" in results[0].error


def test_the_program_that_runs_is_the_inode_that_was_hashed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The digest and the exec must name one FILE, not one path (Sol#1's TOCTOU).

    Resolving once made the two names equal; it did not make them the same
    file. Between the hash and the exec, anything that renames a new inode over
    the program's name — an editor, `git checkout`, a second wrapper — swaps
    the bytes under a digest that has already passed. Executing the OPEN
    DESCRIPTOR closes that: it names the inode that was hashed, even after the
    name stops pointing at it.
    """
    honest = _script(tmp_path / PROGRAM, HONEST)
    witness = tmp_path / WITNESS
    real_run = verify_module.subprocess.run

    def swap_then_run(argv: object, **kwargs: object) -> object:
        honest.unlink()
        _script(tmp_path / PROGRAM, f"#!/bin/sh\ntouch {witness}\nexit 1\n")
        return real_run(argv, **kwargs)

    pins = _pins(honest)
    monkeypatch.setattr(verify_module.subprocess, "run", swap_then_run)

    results = run_checks(_node(), tmp_path, pins)

    assert results[0].provenance_ok is True
    assert results[0].exit_code == 0
    assert not witness.exists()


def test_a_verifier_that_cannot_be_executed_is_a_result_not_an_exception(
    tmp_path: Path,
) -> None:
    """M14: `PermissionError` used to escape `observe()` before any exit record.

    A runner that ran `chmod -R a-x scripts/` therefore left the activation
    with no exit record at all, repeating as `error_transport` until the §10.2
    infra cap burned. The check is honestly pinned here — provenance passes and
    the EXECUTION is what fails.
    """
    program = _script(tmp_path / PROGRAM, HONEST, executable=False)
    assert not tmp_path.joinpath(PROGRAM).stat().st_mode & stat.S_IXUSR

    results = run_checks(_node(), tmp_path, _pins(program))

    assert results[0].provenance_ok is True
    assert results[0].exit_code == REFUSED_EXIT_CODE
    assert results[0].error is not None
    assert "Permission denied" in results[0].error


def test_an_unpinned_program_is_refused_before_it_can_run(tmp_path: Path) -> None:
    """§7.3: no pinned digest means no provenance, and no execution."""
    witness = tmp_path / WITNESS
    _script(tmp_path / PROGRAM, f"#!/bin/sh\ntouch {witness}\nexit 0\n")

    results = run_checks(_node(), tmp_path, {})

    assert not witness.exists()
    assert results[0].provenance_ok is False


def test_the_verify_tree_is_a_clean_checkout_of_the_named_commit(
    tmp_path: Path,
) -> None:
    """B1: the checks get the artifact's tree, not whatever is lying around."""
    repo = make_repo(tmp_path)
    base = head_of(repo)
    config = make_config(repo, tmp_path, fake_proc=False)
    git = make_git(config)
    paths = make_paths(config, "wf-verify")
    (repo / "src" / "feature.py").write_text("value = 2\n", encoding="utf-8")
    later = commit_all(repo, "a second commit")
    (repo / "src" / "feature.py").write_text("uncommitted\n", encoding="utf-8")

    with VerifyTree(git, paths, base) as tree:
        assert git.head_commit(cwd=tree) == base
        assert git.status_paths(cwd=tree) == ()
        assert (tree / "src" / "feature.py").read_text(
            encoding="utf-8"
        ) == "value = 1\n"

    assert not paths.verify_tree.exists()
    assert base != later


def test_the_verify_tree_is_rebuilt_over_a_crashed_predecessor(
    tmp_path: Path,
) -> None:
    """A wrapper killed mid-check leaves a checkout behind; the next one still runs."""
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path, fake_proc=False)
    paths = make_paths(config, "wf-verify")
    paths.verify_tree.mkdir(parents=True)
    (paths.verify_tree / "leftover").write_text("junk\n", encoding="utf-8")

    with VerifyTree(make_git(config), paths, head_of(repo)) as tree:
        assert not (tree / "leftover").exists()


def test_an_empty_verify_command_is_refused(tmp_path: Path) -> None:
    """A check with no program cannot be hashed, so it is not run."""
    with pytest.raises(VerifyTreeError, match="no program"):
        run_checks(_node(cmd=" "), tmp_path, {})


def test_the_pinned_digests_have_a_producer_that_matches_the_reader(
    tmp_path: Path,
) -> None:
    """m23: `pinned_verifier_digests` READ a convention nothing wrote.

    The keys were only ever built by hand, so nothing guaranteed the producer
    and the reader agreed on them — and §7.3's claim is precisely that the
    digest recorded at instantiation is the one checked before execution.
    """
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path, fake_proc=False)
    _, store = make_store(tmp_path, head_of(repo))
    definition = load_definition()
    settings = pin_verifier_digests(definition.document, repo)
    root = store.create_root(
        instance_key="pins", definition=definition, resolved_config=settings
    )

    produced = {setting.key: str(setting.value) for setting in settings}
    read_back = pinned_verifier_digests(root)

    assert produced
    assert read_back == produced
    assert config.repo_root == repo
    executed = run_checks(node_of(definition.document, IMPLEMENT), repo, read_back)
    assert executed[0].provenance_ok is True


def test_a_directory_at_the_verifier_path_is_refused_not_raised(
    tmp_path: Path,
) -> None:
    """Sol#17: `os.open` on a directory SUCCEEDS; `os.pread` on it does not.

    So the descriptor was taken, `_digest_of` raised `IsADirectoryError` from
    inside the loop, and it escaped `run_checks` → `observe()` entirely — no
    exit record, and nothing in §5.6 recovery re-runs §7, so the activation was
    wedged. Committing a directory at a verifier's declared path is something
    the runner being graded can arrange. §7.3 answers this with a REFUSED
    verdict like any other unestablished provenance.
    """
    (tmp_path / PROGRAM).mkdir(parents=True)
    honest = _script(tmp_path / "elsewhere.sh", HONEST)

    results = run_checks(_node(), tmp_path, _pins(honest))

    assert results[0].provenance_ok is False
    assert results[0].exit_code == REFUSED_EXIT_CODE
    assert results[0].script_digest == ""


def test_a_fifo_at_the_verifier_path_is_refused_rather_than_read(
    tmp_path: Path,
) -> None:
    """The same guard, for the case where reading would BLOCK rather than raise.

    A named pipe is openable and readable; `_digest_of` would sit on the first
    `pread` until somebody wrote to it, holding the whole §7 computation — and
    the wrapper's own `max_wall` does not cover its own post-exit work.
    """
    program = tmp_path / PROGRAM
    program.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(program)
    honest = _script(tmp_path / "elsewhere.sh", HONEST)

    results = run_checks(_node(), tmp_path, _pins(honest))

    assert results[0].provenance_ok is False
    assert results[0].exit_code == REFUSED_EXIT_CODE
