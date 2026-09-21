"""Command-line entry point for ledger export, import and reconcile (§3.2, §3.6).

`wf ledger export <task>` and `wf ledger import` in the plan's vocabulary; this
repository spells its entry points `python -m workflow_interpreter.<package>`
(see `workflow_interpreter/costs/__main__.py`), and authority arrives the same
way it does there — as an explicit `--config` file, never from the environment.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio.config import DEFAULT_SSH_KEYGEN
from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.contractor.tracker_wiring import (
    attention_writer,
    repair_mirror,
    tracker_for,
)
from workflow_interpreter.contracts.run_identity import (
    ComponentKind,
    safe_component,
)
from workflow_interpreter.foreman.config import ForemanConfig, load_config
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.ledger.archive import archive_task
from workflow_interpreter.ledger.checkpoint import rebuild_sources
from workflow_interpreter.ledger.constants import (
    CHECKPOINT_REF_TEMPLATE,
    EXPORT_REF_TEMPLATE,
    EXPORT_SUFFIX,
)
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.export import (
    import_exports,
    pin_export,
    write_landed_export,
)
from workflow_interpreter.ledger.paths import export_dir, ledger_path
from workflow_interpreter.ledger.reconcile import ATTENTION_LABEL, AttentionReconciler
from workflow_interpreter.ledger.reverify import TrustAnchor, verify_export

PROG: Final[str] = "python -m workflow_interpreter.ledger"
COMMAND_EXPORT: Final[str] = "export"
COMMAND_PIN_EXPORT: Final[str] = "pin-export"
COMMAND_IMPORT: Final[str] = "import"
COMMAND_RECONCILE: Final[str] = "reconcile"
COMMAND_VERIFY: Final[str] = "verify"
COMMAND_ARCHIVE: Final[str] = "archive"
EXIT_OK: Final[int] = 0
EXIT_REFUSED: Final[int] = 2

_MSG_NO_EXPORTS: Final[str] = (
    "ledger: nothing to rebuild from — no export files under {directory} and "
    "no checkpoint under {prefix}\n"
)
_MSG_REFUSED: Final[str] = "ledger: {reason}\n"
_MSG_EXPORTED: Final[str] = "exported {task_id} to {path}\n"
_MSG_PINNED: Final[str] = "pinned {task_id}: {ref} -> {oid}\n"
_MSG_IMPORTED: Final[str] = "imported {task_id} from {path}\n"
_MSG_RECONCILED: Final[str] = (
    "reconciled {task_id}: {label} {presence}, generation {generation}, "
    "{acked} row(s) acked\n"
)
_MSG_NOTHING_DUE: Final[str] = "reconciled {task_id}: nothing due\n"
_MSG_CONFLICTS: Final[str] = (
    "  {count} mirror intent(s) the tracker REFUSED: {refs}\n"
    "  the row retires either way; the tracker disagrees about these items\n"
)
_MSG_APPROVAL: Final[str] = (
    "{status} {gate_id} {fingerprint} ({principal}, {namespace})\n"
)
_MSG_APPROVAL_REASON: Final[str] = "  {reason}\n"
_MSG_VERIFIED: Final[str] = "verified {count} approval(s) of {task_id} from {path}\n"
_MSG_NOT_VERIFIED: Final[str] = (
    "refused {refused} of {count} approval(s) of {task_id} from {path}\n"
)
_MSG_ANCHORS: Final[str] = (
    "bytes valid: {bytes_valid}; export pinned: {pinned} ({anchor}); signer "
    "trusted: {trusted}; historical entry unchanged: {unchanged}\n"
)
_MSG_NO_ANCHOR: Final[str] = "no anchor"
"""What the anchor field says when neither history nor a ref named an oid."""
_MSG_NO_TRUST_ROOT: Final[str] = (
    "no allowed_signers trust root: pass --allowed-signers, or give the "
    "config a [signing] section. An export cannot vouch for its own signer"
)
_YES: Final[str] = "yes"
_NO: Final[str] = "no"
_MSG_ARCHIVED: Final[str] = (
    "archived {task_id} to {bundle}: {refs} ref(s) and {folders} run folder(s) "
    "removed\n"
)


def _answer(value: bool) -> str:
    """One anchor's answer, printed rather than collapsed into an exit code."""
    return _YES if value else _NO


_PRESENT: Final[str] = "present"
_ABSENT: Final[str] = "absent"


def _parser() -> argparse.ArgumentParser:
    """Build the finite ledger CLI vocabulary."""
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument("--config", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser(
        COMMAND_EXPORT, help="write one task's rows to .wf/export/<task>.jsonl"
    )
    export.add_argument("task_id")
    pin = commands.add_parser(
        COMMAND_PIN_EXPORT,
        help=(
            "re-pin refs/wf/exports/<task> from the export file already on "
            "disk and record its oid — the recovery for a crash between the "
            "write and the pin; it never re-exports"
        ),
    )
    pin.add_argument("task_id")
    restore = commands.add_parser(
        COMMAND_IMPORT,
        help=(
            "rebuild tasks from .wf/export/ and refs/wf/checkpoints/, under "
            "the exclusive fence"
        ),
    )
    restore.add_argument(
        "task_ids",
        nargs="*",
        help=(
            "the tasks the ledger is rebuilt from — each from its committed "
            "export, or from its checkpoint ref when it never closed; every "
            "task some anchor describes when none is named. An import "
            "REPLACES the exportable state, so a task no named anchor "
            "describes does not survive it"
        ),
    )
    reconcile = commands.add_parser(
        COMMAND_RECONCILE,
        help="drain one task's unacked attention projections onto its bead",
    )
    reconcile.add_argument("task_id")
    verify = commands.add_parser(
        COMMAND_VERIFY,
        help=(
            "re-verify every approval of a task from its committed export, "
            "anchored on the export pin in git and an allowed_signers trust "
            "root — no ledger database and no wrapper root"
        ),
    )
    verify.add_argument("task_id")
    verify.add_argument(
        "--allowed-signers",
        type=Path,
        default=None,
        help=(
            "the trust root the signer must appear in; defaults to the "
            "allow-list the config's [signing] section names. It is read from "
            "OUTSIDE the export on purpose: an export carries its own key"
        ),
    )
    archive = commands.add_parser(
        COMMAND_ARCHIVE,
        help=(
            "bundle a closed task's refs/wf/<root>/ to a path outside the "
            "repository, verify the bundle, then delete the run folders and "
            "the refs — manual, and refused without a verified bundle"
        ),
    )
    archive.add_argument("task_id")
    archive.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="where the git bundle is written; outside the repository",
    )
    return parser


def _exports(config: ForemanConfig, task_ids: Sequence[str]) -> tuple[Path, ...]:
    """The sources a rebuild reads, named or discovered in `(task)` order.

    Each task's CLOSE anchor where it has one, and its checkpoint otherwise
    (§3.9, R10): a task that never landed has no committed file, and before S7
    that meant a deleted ledger lost it. `rebuild_sources` owns the precedence
    so the CLI cannot spell it a second way.
    """
    return rebuild_sources(Git(config.inspector), config.repo_root, task_ids)


def _reconcile(config: ForemanConfig, task_id: str) -> int:
    """Drain the unacked attention projections of one task (§3.2.4).

    The bd client is built HERE and injected: a CLI is a composition root, and
    the reconciler must not construct its own transport.
    """
    with open_ledger(config.repo_root, config.wrapper_root) as database:
        writer = attention_writer(database, tracker_for(config.tracker))
        result = AttentionReconciler(database, writer).drain(task_id)
        # The reconciler now only ENQUEUES (§3.3). `wf ledger reconcile` is a
        # human asking for the mirror to be caught up, so it repairs it: the
        # stranded claim §3.4 names this command for, then the drain — unlike
        # a tick, which leaves the drain to the driver's exit.
        drained = repair_mirror(config, database, Git(config.inspector), task_id)
    if drained.conflicts:
        sys.stdout.write(
            _MSG_CONFLICTS.format(
                count=len(drained.conflicts), refs=", ".join(drained.conflicts)
            )
        )
    if not result.written:
        sys.stdout.write(_MSG_NOTHING_DUE.format(task_id=task_id))
        return EXIT_OK
    sys.stdout.write(
        _MSG_RECONCILED.format(
            task_id=task_id,
            label=ATTENTION_LABEL,
            presence=_PRESENT if result.wanted else _ABSENT,
            generation=result.generation,
            acked=result.acked,
        )
    )
    return EXIT_OK


def _verify(config: ForemanConfig, task_id: str, allowed_signers: Path | None) -> int:
    """Re-verify one task's approvals from `.wf/export/<task>.jsonl` (§3.6, D21).

    Deliberately the one ledger command that never opens the LEDGER: the bytes
    half of the proof is that the export is sufficient, so reading the database
    would make it vacuous. Provenance is the other half and it may not come
    from the export — the git pin and the operator's trust root answer it, and
    the four answers are printed separately.
    """
    path = export_dir(config.repo_root) / f"{task_id}{EXPORT_SUFFIX}"
    trust = allowed_signers or (
        None if config.signing is None else config.signing.allowed_signers_path
    )
    if trust is None:
        sys.stderr.write(_MSG_REFUSED.format(reason=_MSG_NO_TRUST_ROOT))
        return EXIT_REFUSED
    verdict = verify_export(
        path,
        task_id,
        TrustAnchor(repo_root=config.repo_root, allowed_signers=trust),
        ssh_keygen=(
            DEFAULT_SSH_KEYGEN if config.signing is None else config.signing.ssh_keygen
        ),
    )
    results = verdict.approvals
    for result in results:
        sys.stdout.write(
            _MSG_APPROVAL.format(
                status=result.status.value,
                gate_id=result.gate_id,
                fingerprint=result.fingerprint,
                principal=result.principal,
                namespace=result.namespace,
            )
        )
        if result.reason is not None:
            sys.stdout.write(_MSG_APPROVAL_REASON.format(reason=result.reason))
    sys.stdout.write(
        _MSG_ANCHORS.format(
            bytes_valid=_answer(verdict.bytes_valid),
            pinned=_answer(verdict.export_pinned),
            anchor=(_MSG_NO_ANCHOR if verdict.anchor is None else verdict.anchor.value),
            trusted=_answer(verdict.signer_trusted),
            unchanged=_answer(verdict.entry_unchanged),
        )
    )
    for reason in verdict.reasons:
        sys.stdout.write(_MSG_APPROVAL_REASON.format(reason=reason))
    if not verdict.accepted:
        refused = sum(1 for result in results if not result.verified)
        sys.stderr.write(
            _MSG_NOT_VERIFIED.format(
                refused=refused, count=len(results), task_id=task_id, path=path
            )
        )
        return EXIT_REFUSED
    sys.stdout.write(
        _MSG_VERIFIED.format(count=len(results), task_id=task_id, path=path)
    )
    return EXIT_OK


def _pin_export(config: ForemanConfig, task_id: str) -> int:
    """Re-pin one task's export from the bytes already on disk (§3.6).

    The recovery for the one window `ExportPin` cannot make atomic: the file
    was written and the process died before the ref named its blob, so the
    task looks unexported while its whole record is sitting in the checkout.
    """
    git = Git(config.inspector)
    with open_ledger(config.repo_root, config.wrapper_root) as database:
        oid = pin_export(git, database, task_id, config.repo_root)
    sys.stdout.write(
        _MSG_PINNED.format(
            task_id=task_id, ref=EXPORT_REF_TEMPLATE.format(task_id=task_id), oid=oid
        )
    )
    return EXIT_OK


def _archive(config: ForemanConfig, task_id: str, bundle: Path) -> int:
    """Archive one closed task's bytes behind a verified bundle (§3.9, D19)."""
    git = Git(config.inspector)
    with open_ledger(config.repo_root, config.wrapper_root) as database:
        result = archive_task(
            git, database, task_id, bundle=bundle, inspector=config.inspector
        )
    sys.stdout.write(
        _MSG_ARCHIVED.format(
            task_id=result.task_id,
            bundle=result.bundle,
            refs=len(result.refs),
            folders=len(result.run_folders),
        )
    )
    return EXIT_OK


def _validate_ids(args: argparse.Namespace) -> None:
    """Put every task id this invocation names through the ONE grammar (§3.6).

    At the CLI boundary, before a config is loaded or a path, a ref or a lock
    is derived from the id: every verb here takes an operator-typed id, and
    each of them derived a different path from it — `reconcile` a lock under
    the wrapper root, `verify` a file under `.wf/export/`, `import` a ref
    name. `../x` escaped all three, and the fence CREATED the lock it escaped
    to. The foreman CLI has validated its ids all along (invariant G).
    """
    named: list[str] = []
    single = getattr(args, "task_id", None)
    if single is not None:
        named.append(str(single))
    named.extend(str(task_id) for task_id in getattr(args, "task_ids", ()))
    for task_id in named:
        safe_component(task_id, kind=ComponentKind.TASK)


def main(argv: Sequence[str] | None = None) -> int:
    """Export one task, or rebuild tasks from their exports."""
    args = _parser().parse_args(argv)
    try:
        _validate_ids(args)
        config = load_config(args.config)
        repo_root = config.repo_root
        wrapper_root = config.wrapper_root
        if args.command == COMMAND_EXPORT:
            with open_ledger(repo_root, wrapper_root) as database:
                path = write_landed_export(database, args.task_id)
            sys.stdout.write(_MSG_EXPORTED.format(task_id=args.task_id, path=path))
            return EXIT_OK
        if args.command == COMMAND_PIN_EXPORT:
            return _pin_export(config, args.task_id)
        if args.command == COMMAND_RECONCILE:
            return _reconcile(config, args.task_id)
        if args.command == COMMAND_VERIFY:
            return _verify(config, args.task_id, args.allowed_signers)
        if args.command == COMMAND_ARCHIVE:
            return _archive(config, args.task_id, args.bundle)
        paths = _exports(config, args.task_ids)
        if not paths:
            sys.stderr.write(
                _MSG_NO_EXPORTS.format(
                    directory=export_dir(repo_root),
                    prefix=CHECKPOINT_REF_TEMPLATE.format(task_id=""),
                )
            )
            return EXIT_REFUSED
        # The schema has to exist before an import can fill it, and creating it
        # takes the exclusive fence — so the ledger is opened and CLOSED first,
        # rather than held while the import asks for the same fence (§3.4).
        with open_ledger(repo_root, wrapper_root):
            pass
        # ONE call, so the whole set lands under ONE fence and ONE transaction
        # (§3.6): a per-file loop would let a reader in between two files and
        # would leave the first files applied when a later one failed.
        task_ids = import_exports(
            paths,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )
        for task_id, path in zip(task_ids, paths, strict=True):
            sys.stdout.write(_MSG_IMPORTED.format(task_id=task_id, path=path))
    except (OSError, ValueError, ValidationError, StoreError) as exc:
        sys.stderr.write(_MSG_REFUSED.format(reason=exc))
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
