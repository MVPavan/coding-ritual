"""Re-verify a task's approvals from its committed export alone (§3.6, D21).

The point of this module is what it does NOT need: no ledger database, no
wrapper home, no allow-list on disk, no bd. A clone of the repository and the
tracked `.wf/export/<task>.jsonl` are the whole input, because the gate-close
transaction stored the historical trust WITH the bytes — the payload, the
signature, the signer's fingerprint, the exact `allowed_signers` entry that
matched, and the policy in force.

Verification therefore reconstructs the allow-list of the MOMENT from the
stored entry and asks `ssh-keygen -Y verify` about it in the stored namespace,
rather than asking today's allow-list, which may have been rotated, widened or
lost since (`bdio/signing.py` — the allow-list of the moment is what decided).

That is a proof about BYTES, and only about bytes. An export carries its own
`key_blob`, so a tampered file can mint a key, re-sign an altered payload and
replace the entry, and the bytes check would then confirm the attacker's own
trust root. PROVENANCE therefore comes from two anchors OUTSIDE the export,
both of them the operator's rather than the file's:

1. the export bytes must hash to the oid git carries for this task — first
   the blob committed at `.wf/export/<task>.jsonl` in the landed history,
   which is what a plain `git clone` transports, and failing that the blob
   pinned at `refs/wf/exports/<task>` by the close itself (§3.6,
   `bridge/journal.py`), which no default clone fetches; and
2. the signer's fingerprint AND key blob must appear in an `allowed_signers`
   trust root the operator names — the same file `bdio/signing.py` verifies
   against live, or an explicit `--allowed-signers` path.

The verdict names the anchor it used, because "pinned" means a different thing
in a fresh clone (the committed export) than in the repository that ran the
close (its own ref).

`ExportVerdict` reports the four answers separately — bytes valid, export
pinned, signer trusted by the anchor, historical entry still equal to the
anchor entry — so a rotated or re-optioned key is VISIBLE without silently
invalidating the bytes that were signed under the old one.
"""

from __future__ import annotations

import base64
import binascii
import json
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from workflow_interpreter.bdio.errors import PayloadMismatchError
from workflow_interpreter.bdio.signing import (
    AllowedSigner,
    GatePayload,
    SignaturePolicy,
    allowed_signers_line,
    key_fingerprint,
    parse_allowed_signers,
)
from workflow_interpreter.ledger.constants import (
    EXPORT_KIND_ROW,
    EXPORT_REF_TEMPLATE,
    ExportKey,
    LedgerTable,
)
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.paths import export_relpath

_ENCODING: Final[str] = "utf-8"
_BLOB_KEY: Final[str] = "base64"
_ALLOWED_SIGNERS: Final[str] = "allowed_signers"
_SIGNATURE: Final[str] = "payload.sig"
_SSH_KEYGEN: Final[str] = "ssh-keygen"
_VERIFY_TIMEOUT_S: Final[float] = 15.0
_FLAGS_VERIFY: Final[tuple[str, ...]] = ("-Y", "verify")
_FLAG_ALLOWED_SIGNERS: Final[str] = "-f"
_FLAG_PRINCIPAL: Final[str] = "-I"
_FLAG_NAMESPACE: Final[str] = "-n"
_FLAG_SIGNATURE: Final[str] = "-s"

MSG_UNREADABLE: Final[str] = "export {path} is unreadable: {reason}"
MSG_NO_SIGNATURES: Final[str] = "export {path} records no approval"
MSG_BAD_ENTRY: Final[str] = (
    "signature of gate {gate_id} carries no usable allow-list entry: {reason}"
)
MSG_FINGERPRINT: Final[str] = (
    "signature of gate {gate_id} was recorded for {recorded}, but its stored "
    "entry is {entry}"
)
MSG_REFUSED: Final[str] = "signature of gate {gate_id} does not verify: {reason}"
MSG_UNRUNNABLE: Final[str] = "{binary} could not be run: {reason}"
MSG_TRUST_UNREADABLE: Final[str] = "the trust root {path} is unreadable: {reason}"
MSG_NO_PIN: Final[str] = (
    "nothing anchors this export: neither the landed history ({path} in "
    "{head}) nor {ref} names a blob, so it is not the export any close recorded"
)
MSG_PIN_MISMATCH: Final[str] = (
    "the export bytes hash to {found}, but {anchor} names {pinned}"
)
MSG_UNTRUSTED_SIGNER: Final[str] = (
    "the signer of gate {gate_id} ({fingerprint}) is in no entry of the trust "
    "root {path}: the export vouches only for itself"
)
MSG_ENTRY_ROTATED: Final[str] = (
    "the trust root {path} now carries a DIFFERENT entry for {fingerprint} "
    "than the one gate {gate_id} was accepted under"
)
MSG_FOREIGN_APPROVAL: Final[str] = (
    "the approval recorded for gate {gate_id} is not an approval of a gate of "
    "task {task_id} this export carries: {reason}"
)
MSG_BAD_ROW: Final[str] = "a {table} row of this export is unusable: {reason}"

_NO_GATE_ROW: Final[str] = "the export declares no gate {gate_id}"
_GATE_OF_OTHER_TASK: Final[str] = "its gate belongs to task {task_id}"
_UNPARSEABLE_PAYLOAD: Final[str] = "the signed bytes are not a gate payload: {reason}"
_PAYLOAD_FIELD: Final[str] = (
    "the signed payload names {field} {found!r}, and the gate it closed carries "
    "{expected!r}"
)
_UNRECORDED_NONCE: Final[str] = (
    "the export records no nonce {nonce!r} consumed by that gate"
)
_FIELD_ROOT_ID: Final[str] = "root_id"
_FIELD_GATE_KEY: Final[str] = "gate_key"

_GIT: Final[str] = "git"
_GIT_TIMEOUT_S: Final[float] = 15.0
_FLAGS_HASH_OBJECT: Final[tuple[str, ...]] = ("hash-object", "-t", "blob", "--")
_FLAGS_REV_PARSE: Final[tuple[str, ...]] = ("rev-parse", "--verify", "--quiet")
_HEAD: Final[str] = "HEAD"
_COMMITTED_BLOB: Final[str] = "{commit}:{path}"


class ExportAnchor(StrEnum):
    """Where the oid this export is checked against came from (§3.6, D21).

    Ordered by what a plain `git clone` actually transports. The committed
    blob is in the landed history every clone fetches; `refs/wf/exports/<task>`
    is written by the close in the repository that ran it and is NOT fetched by
    a default clone, so it answers only where it was published.
    """

    COMMITTED = "the committed export in HEAD"
    REF = "the export ref"


class ApprovalStatus(StrEnum):
    """Whether one recorded approval still verifies against its own trust."""

    VERIFIED = "verified"
    REFUSED = "refused"


class ApprovalResult(BaseModel):
    """One approval's re-verification, named by the gate it closed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str
    status: ApprovalStatus
    fingerprint: str
    principal: str
    namespace: str
    reason: str | None = None

    @property
    def verified(self) -> bool:
        """Whether this approval was accepted on re-verification."""
        return self.status is ApprovalStatus.VERIFIED


class StoredSignature(BaseModel):
    """One `signatures` row as the export carries it (§3.3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str
    payload_bytes: bytes
    signature_bytes: bytes
    signer_fingerprint: str
    signer: AllowedSigner
    policy: SignaturePolicy


class ExportGate(BaseModel):
    """One `gates` row as the export carries it (§3.3).

    Only the columns an approval is bound to: which task owns the gate, and the
    instance and gate identity the signed payload has to name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str
    task_id: str
    root_id: str
    gate_key: str


class ExportNonce(BaseModel):
    """One `nonces` row — which gate this export records spending a nonce."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nonce: str
    gate_id: str


class ExportRows(BaseModel):
    """The rows a re-verification reads out of one export file (§3.3, §3.6).

    The approvals AND the gate rows they claim to close, because an approval on
    its own says nothing about whose gate it approved: the binding check reads
    both out of the SAME file.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    signatures: tuple[StoredSignature, ...]
    gates: tuple[ExportGate, ...]
    nonces: tuple[ExportNonce, ...]

    def gate(self, gate_id: str) -> ExportGate | None:
        """The gate row this export carries for `gate_id`, if it carries one."""
        return next((row for row in self.gates if row.gate_id == gate_id), None)

    def consumed_by(self, nonce: str) -> str | None:
        """Which gate this export records as having consumed `nonce`."""
        return next((row.gate_id for row in self.nonces if row.nonce == nonce), None)


def read_export_rows(path: Path) -> ExportRows:
    """Every row one export file records that an approval is checked against."""
    try:
        lines = path.read_bytes().splitlines()
    except OSError as error:
        raise LedgerExportError(
            MSG_UNREADABLE.format(path=path, reason=error)
        ) from error
    rows = tuple(_rows(path, lines))
    return ExportRows(
        signatures=tuple(
            _stored(row) for table, row in rows if table == LedgerTable.SIGNATURES.value
        ),
        gates=tuple(
            _gate(row) for table, row in rows if table == LedgerTable.GATES.value
        ),
        nonces=tuple(
            _nonce(row) for table, row in rows if table == LedgerTable.NONCES.value
        ),
    )


def read_signatures(path: Path) -> tuple[StoredSignature, ...]:
    """Every approval one export file records, in the order it was written."""
    return read_export_rows(path).signatures


def _rows(
    path: Path, lines: Sequence[bytes]
) -> Iterator[tuple[str, dict[str, object]]]:
    """Every row line as its table and columns; the first bad one refuses the file."""
    for raw in lines:
        if not raw.strip():
            continue
        try:
            line = json.loads(raw)
        except ValueError as error:
            raise LedgerExportError(
                MSG_UNREADABLE.format(path=path, reason=error)
            ) from error
        if not isinstance(line, dict):
            raise LedgerExportError(
                MSG_UNREADABLE.format(path=path, reason="line is not an object")
            )
        if line.get(ExportKey.KIND.value) != EXPORT_KIND_ROW:
            continue
        table = line.get(ExportKey.TABLE.value)
        if not isinstance(table, str):
            continue
        row = line.get(ExportKey.ROW.value)
        if not isinstance(row, dict):
            raise LedgerExportError(
                MSG_UNREADABLE.format(path=path, reason=f"{table} row is not an object")
            )
        yield table, row


def _stored(row: dict[str, object]) -> StoredSignature:
    """One parsed signature row, with its historical trust rehydrated."""
    gate_id = str(row.get("gate_id"))
    try:
        signer = AllowedSigner.model_validate_json(str(row["allowed_signers_entry"]))
        policy = SignaturePolicy.model_validate_json(str(row["policy_json"]))
        return StoredSignature(
            gate_id=gate_id,
            payload_bytes=_blob(row["payload_bytes"]),
            signature_bytes=_blob(row["signature_bytes"]),
            signer_fingerprint=str(row["signer_fingerprint"]),
            signer=signer,
            policy=policy,
        )
    except (KeyError, ValueError, ValidationError) as error:
        raise LedgerExportError(
            MSG_BAD_ENTRY.format(gate_id=gate_id, reason=error)
        ) from error


def _gate(row: dict[str, object]) -> ExportGate:
    """One parsed `gates` row — the gate identity an approval is bound to."""
    try:
        return ExportGate(
            gate_id=str(row["gate_id"]),
            task_id=str(row["task_id"]),
            root_id=str(row["root_id"]),
            gate_key=str(row["gate_key"]),
        )
    except (KeyError, ValidationError) as error:
        raise LedgerExportError(
            MSG_BAD_ROW.format(table=LedgerTable.GATES.value, reason=error)
        ) from error


def _nonce(row: dict[str, object]) -> ExportNonce:
    """One parsed `nonces` row — the nonce a gate of this export spent."""
    try:
        return ExportNonce(nonce=str(row["nonce"]), gate_id=str(row["gate_id"]))
    except (KeyError, ValidationError) as error:
        raise LedgerExportError(
            MSG_BAD_ROW.format(table=LedgerTable.NONCES.value, reason=error)
        ) from error


def _blob(value: object) -> bytes:
    """A BLOB column as the export carries it — a single-key base64 object."""
    if not isinstance(value, dict) or set(value) != {_BLOB_KEY}:
        raise ValueError("column is not an exported BLOB")
    try:
        return base64.b64decode(str(value[_BLOB_KEY]), validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"exported BLOB is not base64: {error}") from error


def verify_signature(
    stored: StoredSignature, *, ssh_keygen: str = _SSH_KEYGEN
) -> ApprovalResult:
    """Re-verify one approval against the allow-list entry it was accepted by.

    Three independent refusals, the same set `GateVerifier` applies live minus
    the ones that need a running instance: the stored entry must be the key the
    approval names, the signature must verify over the stored payload bytes in
    the stored namespace, and the entry must permit that namespace.
    """
    principal = stored.signer.principals[0]
    namespace = stored.policy.namespace
    try:
        blob = base64.b64decode(stored.signer.key_blob, validate=True)
    except (binascii.Error, ValueError) as error:
        return _refused(stored, principal, namespace, str(error))
    if key_fingerprint(blob) != stored.signer_fingerprint:
        return _refused(
            stored,
            principal,
            namespace,
            MSG_FINGERPRINT.format(
                gate_id=stored.gate_id,
                recorded=stored.signer_fingerprint,
                entry=key_fingerprint(blob),
            ),
        )
    if not stored.signer.signs_in(namespace):
        return _refused(
            stored, principal, namespace, f"entry may not sign in {namespace!r}"
        )
    with tempfile.TemporaryDirectory(prefix="wf-reverify-") as directory:
        work = Path(directory)
        allow_list = work / _ALLOWED_SIGNERS
        allow_list.write_text(allowed_signers_line(stored.signer), encoding=_ENCODING)
        signature = work / _SIGNATURE
        signature.write_bytes(stored.signature_bytes)
        try:
            completed = subprocess.run(
                [
                    ssh_keygen,
                    *_FLAGS_VERIFY,
                    _FLAG_ALLOWED_SIGNERS,
                    str(allow_list),
                    _FLAG_PRINCIPAL,
                    principal,
                    _FLAG_NAMESPACE,
                    namespace,
                    _FLAG_SIGNATURE,
                    str(signature),
                ],
                input=stored.payload_bytes,
                capture_output=True,
                timeout=_VERIFY_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise LedgerExportError(
                MSG_UNRUNNABLE.format(binary=ssh_keygen, reason=error)
            ) from error
    if completed.returncode != 0:
        return _refused(
            stored,
            principal,
            namespace,
            completed.stderr.decode(_ENCODING, "replace").strip(),
        )
    return ApprovalResult(
        gate_id=stored.gate_id,
        status=ApprovalStatus.VERIFIED,
        fingerprint=stored.signer_fingerprint,
        principal=principal,
        namespace=namespace,
    )


def _refused(
    stored: StoredSignature, principal: str, namespace: str, reason: str
) -> ApprovalResult:
    """A refusal that still names who was claimed to have signed what."""
    return ApprovalResult(
        gate_id=stored.gate_id,
        status=ApprovalStatus.REFUSED,
        fingerprint=stored.signer_fingerprint,
        principal=principal,
        namespace=namespace,
        reason=MSG_REFUSED.format(gate_id=stored.gate_id, reason=reason),
    )


def verify_approvals(
    path: Path, *, ssh_keygen: str = _SSH_KEYGEN
) -> tuple[ApprovalResult, ...]:
    """Re-verify every approval one exported task records, or refuse the file.

    The BYTES half of D21, and nothing more: it answers "were these payloads
    signed by the key this file names", not "is that key anyone's". The
    provenance half is `verify_export`.
    """
    stored = read_signatures(path)
    if not stored:
        raise LedgerExportError(MSG_NO_SIGNATURES.format(path=path))
    return tuple(verify_signature(item, ssh_keygen=ssh_keygen) for item in stored)


class TrustAnchor(BaseModel):
    """The two things a re-verification may NOT take from the export (§3.6).

    A clone of the repository, because the export blob is pinned in it, and the
    operator's `allowed_signers` file, because a fingerprint the export carries
    is only a name until some trust root outside the export answers for it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_root: Path
    allowed_signers: Path


class ExportVerdict(BaseModel):
    """What a re-verification can and cannot say about one exported task.

    Four independent answers, because collapsing them hides which one failed:
    a rotated key leaves `bytes_valid` true and `signer_trusted` false, and an
    export nobody pinned leaves both true and `export_pinned` false.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    path: Path
    approvals: tuple[ApprovalResult, ...]
    bytes_valid: bool
    export_pinned: bool
    signer_trusted: bool
    entry_unchanged: bool
    blob_oid: str | None = None
    pinned_oid: str | None = None
    anchor: ExportAnchor | None = None
    """Which source named `pinned_oid` — a verdict that does not say where its
    provenance came from is not one an operator can weigh (§3.6)."""
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        """Whether every answer provenance depends on came back yes.

        `entry_unchanged` is deliberately NOT one of them: re-optioning a live
        entry is an operator act, and it does not unsign what was signed.
        """
        return self.bytes_valid and self.export_pinned and self.signer_trusted


def read_trust_root(path: Path) -> tuple[AllowedSigner, ...]:
    """Parse the operator's `allowed_signers` file — the anchor, not the export."""
    try:
        text = path.read_text(encoding=_ENCODING)
    except OSError as error:
        raise LedgerExportError(
            MSG_TRUST_UNREADABLE.format(path=path, reason=error)
        ) from error
    return parse_allowed_signers(text, path)


def _git_text(anchor: TrustAnchor, *args: str) -> str | None:
    """One read-only git command in the clone, or `None` when it answers nothing.

    `subprocess` rather than `supervisor.gitio.Git`: this module must run in a
    bare clone with no wrapper root and no config, which is exactly what makes
    the check worth anything, and `Git` is constructed from a `SupervisorConfig`
    that such a clone cannot supply.
    """
    try:
        completed = subprocess.run(
            [_GIT, *args],
            cwd=anchor.repo_root,
            capture_output=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LedgerExportError(
            MSG_UNRUNNABLE.format(binary=_GIT, reason=error)
        ) from error
    if completed.returncode != 0:
        return None
    return completed.stdout.decode(_ENCODING, "replace").strip() or None


def _anchor_oid(
    anchor: TrustAnchor, task_id: str
) -> tuple[ExportAnchor | None, str | None, str]:
    """The oid this export must hash to, and which anchor named it.

    Transported history first: `HEAD:.wf/export/<task>.jsonl` is the export the
    orchestrator committed beside the landed work, so every clone carries it.
    The close's own `refs/wf/exports/<task>` is the fallback, because a default
    clone does not fetch custom refs — it proves provenance only in a
    repository where the close ran or where the ref was deliberately published.
    """
    relative = export_relpath(task_id)
    committed = _git_text(
        anchor, *_FLAGS_REV_PARSE, _COMMITTED_BLOB.format(commit=_HEAD, path=relative)
    )
    if committed is not None:
        return ExportAnchor.COMMITTED, committed, relative
    ref = EXPORT_REF_TEMPLATE.format(task_id=task_id)
    return (
        (None, None, relative)
        if (pinned := _git_text(anchor, *_FLAGS_REV_PARSE, ref)) is None
        else (ExportAnchor.REF, pinned, relative)
    )


def _pin_check(
    anchor: TrustAnchor, task_id: str, path: Path
) -> tuple[bool, str | None, str | None, ExportAnchor | None, tuple[str, ...]]:
    """Whether these export bytes are the ones git carries for this task (§3.6)."""
    source, pinned, relative = _anchor_oid(anchor, task_id)
    blob = _git_text(anchor, *_FLAGS_HASH_OBJECT, str(path))
    if source is None or pinned is None:
        return (
            False,
            blob,
            None,
            None,
            (
                MSG_NO_PIN.format(
                    path=relative,
                    head=_HEAD,
                    ref=EXPORT_REF_TEMPLATE.format(task_id=task_id),
                ),
            ),
        )
    if blob != pinned:
        return (
            False,
            blob,
            pinned,
            source,
            (MSG_PIN_MISMATCH.format(found=blob, anchor=source.value, pinned=pinned),),
        )
    return True, blob, pinned, source, ()


def _signer_check(
    stored: Sequence[StoredSignature], anchor: TrustAnchor
) -> tuple[bool, bool, tuple[str, ...]]:
    """Whether the trust root — not the export — answers for every signer."""
    entries = read_trust_root(anchor.allowed_signers)
    trusted = True
    unchanged = True
    reasons: list[str] = []
    for item in stored:
        match = next(
            (
                entry
                for entry in entries
                if entry.fingerprint == item.signer_fingerprint
                and entry.key_blob == item.signer.key_blob
            ),
            None,
        )
        if match is None:
            trusted = False
            reasons.append(
                MSG_UNTRUSTED_SIGNER.format(
                    gate_id=item.gate_id,
                    fingerprint=item.signer_fingerprint,
                    path=anchor.allowed_signers,
                )
            )
            continue
        if match != item.signer:
            unchanged = False
            reasons.append(
                MSG_ENTRY_ROTATED.format(
                    path=anchor.allowed_signers,
                    fingerprint=item.signer_fingerprint,
                    gate_id=item.gate_id,
                )
            )
    return trusted, unchanged, tuple(reasons)


def _binding_reason(
    stored: StoredSignature, rows: ExportRows, task_id: str
) -> str | None:
    """Why this approval is not one of THIS task's gates, or `None` when it is.

    The close-time identity of `bdio/gates.py` (`_assert_payload_matches`,
    `_assert_nonce_unused`), re-asked of the export's OWN rows because a
    re-verification has no instance to ask: the signed payload must name the
    root and the `gate_key` of a `gates` row this file carries for `task_id`,
    and the nonce it spends must be the one this file records that same gate
    consuming.

    Without it, a valid export of ANOTHER task left at this task's committed
    path passes the signature, the git pin and the trust root, and its
    approvals are reported as this task's.
    """
    gate = rows.gate(stored.gate_id)
    if gate is None:
        return _NO_GATE_ROW.format(gate_id=stored.gate_id)
    if gate.task_id != task_id:
        return _GATE_OF_OTHER_TASK.format(task_id=gate.task_id)
    try:
        payload = GatePayload.model_validate_json(stored.payload_bytes)
    except (ValidationError, ValueError, PayloadMismatchError) as error:
        return _UNPARSEABLE_PAYLOAD.format(reason=error)
    for field, found, expected in (
        (_FIELD_ROOT_ID, payload.root_id, gate.root_id),
        (_FIELD_GATE_KEY, payload.gate_key, gate.gate_key),
    ):
        if found != expected:
            return _PAYLOAD_FIELD.format(field=field, found=found, expected=expected)
    if rows.consumed_by(payload.nonce) != gate.gate_id:
        return _UNRECORDED_NONCE.format(nonce=payload.nonce)
    return None


def _bound_approval(
    stored: StoredSignature, rows: ExportRows, task_id: str, *, ssh_keygen: str
) -> ApprovalResult:
    """One approval, re-verified only once it is an approval of THIS task.

    An approval that names no gate of this task is reported UNVERIFIED with the
    reason, never raised: the export may be a perfectly well-formed export of
    something else, and saying so is the answer.
    """
    reason = _binding_reason(stored, rows, task_id)
    if reason is None:
        return verify_signature(stored, ssh_keygen=ssh_keygen)
    return ApprovalResult(
        gate_id=stored.gate_id,
        status=ApprovalStatus.REFUSED,
        fingerprint=stored.signer_fingerprint,
        principal=stored.signer.principals[0],
        namespace=stored.policy.namespace,
        reason=MSG_FOREIGN_APPROVAL.format(
            gate_id=stored.gate_id, task_id=task_id, reason=reason
        ),
    )


def verify_export(
    path: Path,
    task_id: str,
    anchor: TrustAnchor,
    *,
    ssh_keygen: str = _SSH_KEYGEN,
) -> ExportVerdict:
    """Re-verify one task's approvals, and anchor them outside the export (D21).

    Four questions, asked in the order their answers depend on each other: is
    each recorded approval an approval of a gate of THIS task, are the
    signatures over those bytes valid, are these the bytes git pinned for this
    task, and is the key that signed them one the operator's trust root knows.
    The first two are answered from the export; the other two never are.

    The binding question comes first because the other three are silent about
    it: another task's valid, pinned, trusted export placed at this task's
    committed path answers all of them yes (`_binding_reason`).
    """
    rows = read_export_rows(path)
    stored = rows.signatures
    if not stored:
        raise LedgerExportError(MSG_NO_SIGNATURES.format(path=path))
    approvals = tuple(
        _bound_approval(item, rows, task_id, ssh_keygen=ssh_keygen) for item in stored
    )
    pinned, blob_oid, pinned_oid, source, pin_reasons = _pin_check(
        anchor, task_id, path
    )
    trusted, unchanged, signer_reasons = _signer_check(stored, anchor)
    return ExportVerdict(
        task_id=task_id,
        path=path,
        approvals=approvals,
        bytes_valid=all(result.verified for result in approvals),
        export_pinned=pinned,
        signer_trusted=trusted,
        entry_unchanged=unchanged,
        blob_oid=blob_oid,
        pinned_oid=pinned_oid,
        anchor=source,
        reasons=(
            *(result.reason for result in approvals if result.reason is not None),
            *pin_reasons,
            *signer_reasons,
        ),
    )
