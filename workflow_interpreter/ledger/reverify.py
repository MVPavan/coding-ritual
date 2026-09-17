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

from workflow_interpreter.bdio.signing import (
    AllowedSigner,
    SignaturePolicy,
    allowed_signers_line,
    key_fingerprint,
)
from workflow_interpreter.ledger.constants import (
    EXPORT_KIND_ROW,
    ExportKey,
    LedgerTable,
)
from workflow_interpreter.ledger.errors import LedgerExportError

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


def read_signatures(path: Path) -> tuple[StoredSignature, ...]:
    """Every approval one export file records, in the order it was written."""
    try:
        lines = path.read_bytes().splitlines()
    except OSError as error:
        raise LedgerExportError(
            MSG_UNREADABLE.format(path=path, reason=error)
        ) from error
    return tuple(_signatures(path, lines))


def _signatures(path: Path, lines: Sequence[bytes]) -> Iterator[StoredSignature]:
    """Parse the signature rows and refuse the file on the first bad one."""
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
        if line.get(ExportKey.TABLE.value) != LedgerTable.SIGNATURES.value:
            continue
        row = line.get(ExportKey.ROW.value)
        if not isinstance(row, dict):
            raise LedgerExportError(
                MSG_UNREADABLE.format(
                    path=path, reason="signature row is not an object"
                )
            )
        yield _stored(row)


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


def verify_export(
    path: Path, *, ssh_keygen: str = _SSH_KEYGEN
) -> tuple[ApprovalResult, ...]:
    """Re-verify every approval one exported task records, or refuse the file."""
    stored = read_signatures(path)
    if not stored:
        raise LedgerExportError(MSG_NO_SIGNATURES.format(path=path))
    return tuple(verify_signature(item, ssh_keygen=ssh_keygen) for item in stored)
