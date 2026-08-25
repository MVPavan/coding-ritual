"""§9 human gates — canonical payload build and signature verification.

**Mechanism choice (flagged).** §9 fixes the payload, the allow-list and the
"verify signature AND fingerprint equality, never just exit 0" rule, but does
not name a signing mechanism (it only mentions `verify-tag` as an example of
the insufficient check). This implementation uses OpenSSH signatures —
`ssh-keygen -Y sign` / `-Y verify` with an `allowed_signers` file — because it
needs no new Python dependency, the allow-list is a single pinned file, and
`-Y verify` reports the signing key's fingerprint so the explicit equality
check §9 demands has something to compare against.

Verification is four independent refusals, all of which must pass:

1. the signature verifies over the canonical payload bytes in this namespace;
2. the signing key maps to a principal in the pinned allow-list;
3. the reported fingerprint is one of the allow-list's fingerprints;
4. the signed bytes are canonical — a signature over a re-encoded payload
   cannot be laundered into a valid approval (same invariant as the pinned
   graph body, §2 rule 8).

Nonce replay and gate-identity cross-checks are §9 too, but they need the gate
bead, so they live in `api.close_gate_verified`.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Final

from pydantic import BaseModel, Field, model_validator

from workflow_interpreter.bdio.config import SigningConfig
from workflow_interpreter.bdio.errors import (
    BdConfigError,
    PayloadMismatchError,
    SignatureRefusedError,
    SignerNotAllowedError,
)
from workflow_interpreter.bdio.wire import (
    CANON_GATE_PAYLOAD,
    WIRE_MODEL,
    JsonSafeInt,
    canonical_json_bytes,
    parse_bound_key,
)
from workflow_interpreter.schema.models import Outcome

_FINGERPRINT_PATTERN: Final[re.Pattern[str]] = re.compile(r"SHA256:[A-Za-z0-9+/=]+")
_SIGNATURE_FILE: Final[str] = "payload.sig"

_FLAG_VERIFY: Final[str] = "-Y"
_OP_VERIFY: Final[str] = "verify"
_OP_FIND_PRINCIPALS: Final[str] = "find-principals"
_FLAG_ALLOWED_SIGNERS: Final[str] = "-f"
_FLAG_PRINCIPAL: Final[str] = "-I"
_FLAG_NAMESPACE: Final[str] = "-n"
_FLAG_SIGNATURE: Final[str] = "-s"

_COMMENT_PREFIX: Final[str] = "#"
_OPTION_SEPARATOR: Final[str] = ","
_NAMESPACES_OPTION: Final[str] = "namespaces="
_CERT_AUTHORITY_OPTION: Final[str] = "cert-authority"
_FINGERPRINT_PREFIX: Final[str] = "SHA256:"
_QUOTE: Final[str] = '"'
_NEGATION_PREFIX: Final[str] = "!"
_WHITESPACE: Final[str] = " \t"
_KEY_TYPE_LENGTH_BYTES: Final[int] = 4
"""An SSH public-key blob opens with a 4-byte big-endian length followed by the
key type string — the authority on what the blob actually is."""
_MIN_BLOB_FIELDS: Final[int] = 2
"""Type string plus at least one key field: ed25519 carries the public key,
RSA `e` and `n`, ECDSA the curve name and the point."""
_REASON_NO_KEY: Final[str] = "no keytype + base64 key pair on the line"
_REASON_NO_PRINCIPAL: Final[str] = "the principals field is empty"
_REASON_NOT_A_KEY_BLOB: Final[str] = (
    "the base64 field does not decode to an SSH public-key blob"
)
_REASON_KEY_TYPE_MISMATCH: Final[str] = (
    "the key blob declares type {found!r}, the line declares {declared!r}"
)
_REASON_CERT_AUTHORITY: Final[str] = (
    "the entry is a cert-authority; §9 verifies signatures by FINGERPRINT "
    "EQUALITY against named keys, and a CA fingerprint is not the fingerprint "
    "of anything that signs — certificate signers are not supported"
)
_KEY_TYPE_PREFIXES: Final[tuple[str, ...]] = (
    "ssh-",
    "ecdsa-",
    "sk-ssh-",
    "sk-ecdsa-",
    "webauthn-sk-ecdsa-",
)
"""An `allowed_signers` line's key type. Everything between the principals
field and this token is the optional options field (sshsig ALLOWED SIGNERS)."""

_MSG_ALLOW_LIST_MISSING: Final[str] = (
    "gate allow-list {path} does not exist; §9 requires a pinned allow-list"
)
_MSG_ALLOW_LIST_UNPARSEABLE: Final[str] = (
    "gate allow-list {path} line {line_no} is not a valid allowed_signers "
    "entry ({reason}); a line the wrapper cannot parse is a key it cannot "
    "hold accountable, so the allow-list is refused whole (§9)"
)
_MSG_NO_KEY_FOR_NAMESPACE: Final[str] = (
    "gate allow-list {path} has no key permitted to sign in namespace {namespace!r}"
)
_MSG_SCHEMA_VERSION: Final[str] = (
    "payload schema_version {found!r} is not the pinned {expected!r} (§9)"
)
_MSG_MUTATION_OUTCOME: Final[str] = (
    "bound_mutation is legal IFF the outcome is {rebudget}; this payload is "
    "outcome={outcome} with bound_mutation {presence} (§9)"
)
_MSG_MUTATION_KEY: Final[str] = (
    "bound_mutation key {key!r} is not in the closed bound vocabulary (§9)"
)
_MSG_ALLOW_LIST_INSIDE: Final[str] = (
    "gate allow-list {path} is inside the bd workspace {workspace}; a foreman "
    "that can write its own allow-list can forge approvals (§9)"
)
_MSG_NO_PRINCIPAL: Final[str] = (
    "no principal in the allow-list matches the signing key: {stderr}"
)
_MSG_VERIFY_FAILED: Final[str] = (
    "signature does not verify for principal {principal!r} in namespace "
    "{namespace!r}: {stderr}"
)
_MSG_NO_FINGERPRINT: Final[str] = (
    "ssh-keygen verified the signature but reported no key fingerprint: {stdout!r}"
)
_MSG_FINGERPRINT_NOT_ALLOWED: Final[str] = (
    "signing key {fingerprint} is not on the pinned allow-list"
)
_MSG_NONCANONICAL: Final[str] = (
    "the signed bytes are not the canonical emission of the payload they "
    "encode; a re-encoded payload is rejected, never normalized (§9)"
)
_MSG_UNPARSEABLE: Final[str] = "the signed bytes are not a valid gate payload: {reason}"
_MSG_TIMEOUT: Final[str] = "ssh-keygen {operation} exceeded its {timeout_s}s timeout"


def _pattern_matches(pattern: str, value: str) -> bool:
    """OpenSSH PATTERNS matching: `*` and `?` are the ONLY metacharacters.

    `fnmatch` additionally honours `[…]` character classes, which OpenSSH does
    not: a literal bracket in a namespace would be read as a class and match
    something else. The translation escapes everything, then re-enables the two
    wildcards OpenSSH defines.
    """
    translated = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    return re.fullmatch(translated, value) is not None


class GateArtifact(BaseModel):
    """What the approval binds to (§9 artifact classes).

    `binds = "immutable"`: the commit and tree OIDs being approved — the
    signature over the OID is the authority. `binds = "mutable"`: the
    document's sha256, re-hashed at close.
    """

    model_config = WIRE_MODEL

    commit_oid: str | None = None
    tree_oid: str | None = None
    sha256: str | None = None


class BoundMutation(BaseModel):
    """A `rebudget` payload's new bound, written to the root with provenance (§9).

    The key must be in the closed bound vocabulary and the value positive;
    that the value actually RAISES the current bound needs the root, so
    `gates.py` checks it where the root is in hand.
    """

    model_config = WIRE_MODEL

    key: str
    value: JsonSafeInt = Field(gt=0)

    @model_validator(mode="after")
    def _assert_known_key(self) -> BoundMutation:
        """Refuse a mutation naming anything outside the §10.4 bound set."""
        if parse_bound_key(self.key) is None:
            raise PayloadMismatchError(_MSG_MUTATION_KEY.format(key=self.key))
        return self


class GatePayload(BaseModel):
    """The canonical payload a human signs (§9).

    Two shape rules live here because they need nothing but the payload: the
    schema version is PINNED (a `wf-gate-payload/2` must not close a v1 gate),
    and `bound_mutation` is legal IFF the outcome is `rebudget`. The artifact
    shape depends on the gate's `binds` mode and is checked in `gates.py`.
    """

    model_config = WIRE_MODEL

    schema_version: str = CANON_GATE_PAYLOAD
    graph_id: str
    root_id: str
    gate_key: str
    outcome: Outcome
    artifact: GateArtifact
    nonce: str
    bound_mutation: BoundMutation | None = None

    @model_validator(mode="after")
    def _assert_payload_shape(self) -> GatePayload:
        """Pin the schema version and the rebudget/mutation biconditional."""
        if self.schema_version != CANON_GATE_PAYLOAD:
            raise PayloadMismatchError(
                _MSG_SCHEMA_VERSION.format(
                    found=self.schema_version, expected=CANON_GATE_PAYLOAD
                )
            )
        is_rebudget = self.outcome is Outcome.REBUDGET
        if is_rebudget != (self.bound_mutation is not None):
            raise PayloadMismatchError(
                _MSG_MUTATION_OUTCOME.format(
                    rebudget=Outcome.REBUDGET.value,
                    outcome=self.outcome.value,
                    presence="present" if self.bound_mutation else "absent",
                )
            )
        return self


class AllowedSigner(BaseModel):
    """One parsed `allowed_signers` entry (sshsig ALLOWED SIGNERS grammar)."""

    model_config = WIRE_MODEL

    principals: tuple[str, ...]
    key_type: str
    fingerprint: str
    namespaces: tuple[str, ...] = ()
    """Empty = the entry carries no `namespaces=` restriction, so the key may
    sign in any namespace. Otherwise an OpenSSH PATTERN-LIST: `*` and `?`
    wildcards, entries prefixed `!` are negations."""

    def signs_in(self, namespace: str) -> bool:
        """Whether this entry permits signatures in `namespace`.

        OpenSSH pattern-list semantics (ssh_config PATTERNS, used by sshsig's
        `namespaces=`): a value matches when at least one positive pattern
        matches AND no negated (`!`) pattern does. Matching positives only made
        `namespaces="*,!wf-gate"` permit `wf-gate` — the one direction this
        parser must never fail in (probed against OpenSSH 9.6, phase-2 r3).
        """
        if not self.namespaces:
            return True
        matched = False
        for pattern in self.namespaces:
            if pattern.startswith(_NEGATION_PREFIX):
                if _pattern_matches(pattern[len(_NEGATION_PREFIX) :], namespace):
                    return False
            elif _pattern_matches(pattern, namespace):
                matched = True
        return matched


class VerifiedApproval(BaseModel):
    """The result of a passing §9 verification — the only way a gate closes."""

    model_config = WIRE_MODEL

    payload: GatePayload
    principal: str
    fingerprint: str
    payload_digest: str


def canonical_payload_bytes(payload: GatePayload) -> bytes:
    """The exact bytes signed and verified — canonical JSON, nulls elided."""
    return canonical_json_bytes(
        payload.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


def payload_digest(payload_bytes: bytes) -> str:
    """sha256 over the signed bytes; recorded on the gate bead as a receipt."""
    return hashlib.sha256(payload_bytes).hexdigest()


def key_fingerprint(blob: bytes) -> str:
    """OpenSSH's `SHA256:` fingerprint of a raw public-key blob.

    sha256 over the base64-decoded blob, re-encoded base64 without padding —
    byte-identical to `ssh-keygen -lf` (asserted against the real tool).
    """
    digest = hashlib.sha256(blob).digest()
    return _FINGERPRINT_PREFIX + base64.b64encode(digest).decode("ascii").rstrip("=")


def parse_allowed_signers(text: str, path: Path) -> tuple[AllowedSigner, ...]:
    """Parse an `allowed_signers` file per the sshsig ALLOWED SIGNERS grammar.

    `principals [options] keytype base64-key [comment]`. The options field is
    optional, so the key type is found by prefix rather than by position, and
    commas inside a quoted option value do not split it. `ssh-keygen -lf` does
    not understand option fields at all: the previous fingerprint extraction
    silently dropped every `namespaces="…"`-hardened line and failed outright
    on an options-only file (probed, phase-2 review).

    A line that does not parse refuses the whole allow-list: a key the wrapper
    cannot read is a key it cannot hold accountable.
    """
    signers: list[AllowedSigner] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(_COMMENT_PREFIX):
            continue
        signers.append(_parse_signer_line(line, line_no, path))
    return tuple(signers)


def _split_unquoted(text: str, separators: str) -> list[str]:
    """Split on any of `separators` that is not inside a double-quoted span."""
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    for char in text:
        if char == _QUOTE:
            quoted = not quoted
        if char in separators and not quoted:
            if current:
                parts.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current))
    return parts


def _parse_signer_line(line: str, line_no: int, path: Path) -> AllowedSigner:
    """One `allowed_signers` entry, or `BdConfigError` naming the line."""

    def refuse(reason: object) -> BdConfigError:
        return BdConfigError(
            _MSG_ALLOW_LIST_UNPARSEABLE.format(
                path=path, line_no=line_no, reason=reason
            )
        )

    fields = _split_unquoted(line, _WHITESPACE)
    key_index = next(
        (
            index
            for index, field in enumerate(fields[1:], start=1)
            if field.startswith(_KEY_TYPE_PREFIXES)
        ),
        None,
    )
    if key_index is None or key_index + 1 >= len(fields):
        raise refuse(_REASON_NO_KEY)
    try:
        blob = base64.b64decode(fields[key_index + 1], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise refuse(exc) from exc
    declared_type = fields[key_index]
    blob_type = _blob_key_type(blob)
    if blob_type is None:
        raise refuse(_REASON_NOT_A_KEY_BLOB)
    if blob_type != declared_type:
        raise refuse(
            _REASON_KEY_TYPE_MISMATCH.format(found=blob_type, declared=declared_type)
        )
    options = _options(fields[1:key_index])
    if any(option.lower() == _CERT_AUTHORITY_OPTION for option in options):
        raise refuse(_REASON_CERT_AUTHORITY)
    principals = tuple(
        part.strip(_QUOTE) for part in _split_unquoted(fields[0], _OPTION_SEPARATOR)
    )
    if not principals:
        raise refuse(_REASON_NO_PRINCIPAL)
    return AllowedSigner(
        principals=principals,
        key_type=declared_type,
        fingerprint=key_fingerprint(blob),
        namespaces=_namespaces_option(options),
    )


def _blob_key_type(blob: bytes) -> str | None:
    """The key type embedded in an SSH public-key blob, or `None` if it is not one.

    The declared keytype token is caller text; the blob is the key. `ssh-ed25519
    AAAA` decodes to three bytes and is not a key at all, yet the wrapper
    fingerprinted it and started up while ssh-keygen reports `invalid key`
    (probed, phase-2 review) — so the blob's own type string is read and
    matched against what the line claims.

    The WHOLE blob is validated, not just its first field: an SSH public key is
    a sequence of length-prefixed strings, and a blob truncated to its type
    string alone still yielded a type here while `ssh-keygen -lf` exited 255
    (probed, phase-2 r3). Every key type carries at least one field after the
    type, and no trailing bytes may be left over.
    """
    fields = _blob_fields(blob)
    if fields is None or len(fields) < _MIN_BLOB_FIELDS:
        return None
    try:
        return fields[0].decode("ascii")
    except UnicodeDecodeError:
        return None


def _blob_fields(blob: bytes) -> list[bytes] | None:
    """An SSH wire blob split into its length-prefixed fields, or `None`.

    `None` means the bytes are not a well-formed sequence at all: a length runs
    past the end, a field is empty where the format has none, or bytes are left
    over after the last field.
    """
    fields: list[bytes] = []
    offset = 0
    while offset < len(blob):
        if len(blob) - offset < _KEY_TYPE_LENGTH_BYTES:
            return None
        length = int.from_bytes(blob[offset : offset + _KEY_TYPE_LENGTH_BYTES], "big")
        start = offset + _KEY_TYPE_LENGTH_BYTES
        end = start + length
        if length == 0 or end > len(blob):
            return None
        fields.append(blob[start:end])
        offset = end
    return fields


def _options(option_fields: list[str]) -> tuple[str, ...]:
    """Every individual option token of an `allowed_signers` options field."""
    return tuple(
        option
        for field in option_fields
        for option in _split_unquoted(field, _OPTION_SEPARATOR)
    )


def _namespaces_option(options: tuple[str, ...]) -> tuple[str, ...]:
    """The `namespaces="a,b"` restriction, if the options field carries one.

    OpenSSH option keywords are case-INSENSITIVE; matching them case-sensitively
    silently dropped a `Namespaces=` restriction and treated the key as
    unrestricted (probed, phase-2 review), which is the one direction this
    parser must never fail in.
    """
    for option in options:
        if option.lower().startswith(_NAMESPACES_OPTION):
            value = option[len(_NAMESPACES_OPTION) :].strip(_QUOTE)
            return tuple(part for part in value.split(_OPTION_SEPARATOR) if part)
    return ()


class GateVerifier:
    """Verifies §9 signed payloads against a pinned, out-of-workspace allow-list."""

    def __init__(self, config: SigningConfig, workspace: Path) -> None:
        path = config.allowed_signers_path
        if not path.is_file():
            raise BdConfigError(_MSG_ALLOW_LIST_MISSING.format(path=path))
        resolved = path.resolve()
        workspace_resolved = workspace.resolve()
        if resolved.is_relative_to(workspace_resolved):
            raise BdConfigError(
                _MSG_ALLOW_LIST_INSIDE.format(
                    path=resolved, workspace=workspace_resolved
                )
            )
        self._config = config
        self._allowed_signers = resolved
        # Parsed at CONSTRUCTION: an unusable allow-list is a configuration
        # failure the tick must see at startup, not a gate refusal a human
        # discovers after signing (§9).
        self._signers = parse_allowed_signers(
            resolved.read_text(encoding="utf-8"), resolved
        )
        if not self.allowed_fingerprints():
            raise BdConfigError(
                _MSG_NO_KEY_FOR_NAMESPACE.format(
                    path=resolved, namespace=config.namespace
                )
            )

    @property
    def allowed_signers_path(self) -> Path:
        """The pinned allow-list this verifier trusts."""
        return self._allowed_signers

    @property
    def signers(self) -> tuple[AllowedSigner, ...]:
        """Every parsed allow-list entry, restrictions included."""
        return self._signers

    def _ssh_keygen(
        self, args: list[str], operation: str, stdin: bytes = b""
    ) -> subprocess.CompletedProcess[bytes]:
        """Run ssh-keygen with no shell and an explicit timeout."""
        argv = [self._config.ssh_keygen, *args]
        try:
            return subprocess.run(
                argv,
                input=stdin,
                capture_output=True,
                timeout=self._config.verify_timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SignatureRefusedError(
                _MSG_TIMEOUT.format(
                    operation=operation, timeout_s=self._config.verify_timeout_s
                )
            ) from exc

    def allowed_fingerprints(self) -> frozenset[str]:
        """Fingerprints permitted to sign in the configured namespace (§9).

        An entry carrying `namespaces="…"` that excludes this namespace is not
        an allowed signer here: honoring the restriction is the point of
        parsing the options field.
        """
        return frozenset(
            signer.fingerprint
            for signer in self._signers
            if signer.signs_in(self._config.namespace)
        )

    def verify(
        self, *, payload_bytes: bytes, signature: bytes, work_dir: Path
    ) -> VerifiedApproval:
        """Verify a detached signature over `payload_bytes`, or refuse.

        `work_dir` is a caller-owned scratch directory (ssh-keygen reads the
        signature from a file); it must not be the bd workspace. The payload
        itself travels on stdin — nothing but the signature is written.
        """
        payload = self._parse_canonical(payload_bytes)
        signature_path = work_dir / _SIGNATURE_FILE
        signature_path.write_bytes(signature)

        principal = self._find_principal(signature_path)
        fingerprint = self._verify_signature(payload_bytes, signature_path, principal)
        if fingerprint not in self.allowed_fingerprints():
            raise SignerNotAllowedError(
                _MSG_FINGERPRINT_NOT_ALLOWED.format(fingerprint=fingerprint)
            )
        return VerifiedApproval(
            payload=payload,
            principal=principal,
            fingerprint=fingerprint,
            payload_digest=payload_digest(payload_bytes),
        )

    @staticmethod
    def _parse_canonical(payload_bytes: bytes) -> GatePayload:
        """Parse the signed bytes and refuse any non-canonical encoding."""
        try:
            parsed = json.loads(payload_bytes)
            payload = GatePayload.model_validate(parsed)
        except (ValueError, TypeError) as exc:
            raise SignatureRefusedError(_MSG_UNPARSEABLE.format(reason=exc)) from exc
        if canonical_payload_bytes(payload) != payload_bytes:
            raise SignatureRefusedError(_MSG_NONCANONICAL)
        return payload

    def _find_principal(self, signature_path: Path) -> str:
        """The allow-list principal the signing key belongs to."""
        completed = self._ssh_keygen(
            [
                _FLAG_VERIFY,
                _OP_FIND_PRINCIPALS,
                _FLAG_SIGNATURE,
                str(signature_path),
                _FLAG_ALLOWED_SIGNERS,
                str(self._allowed_signers),
            ],
            _OP_FIND_PRINCIPALS,
        )
        principals = [
            line.strip()
            for line in completed.stdout.decode("utf-8", "replace").splitlines()
            if line.strip()
        ]
        if completed.returncode != 0 or not principals:
            raise SignerNotAllowedError(
                _MSG_NO_PRINCIPAL.format(
                    stderr=completed.stderr.decode("utf-8", "replace").strip()
                )
            )
        return principals[0]

    def _verify_signature(
        self, payload_bytes: bytes, signature_path: Path, principal: str
    ) -> str:
        """Verify and return the fingerprint ssh-keygen reports for the signer."""
        completed = self._ssh_keygen(
            [
                _FLAG_VERIFY,
                _OP_VERIFY,
                _FLAG_ALLOWED_SIGNERS,
                str(self._allowed_signers),
                _FLAG_PRINCIPAL,
                principal,
                _FLAG_NAMESPACE,
                self._config.namespace,
                _FLAG_SIGNATURE,
                str(signature_path),
            ],
            _OP_VERIFY,
            stdin=payload_bytes,
        )
        if completed.returncode != 0:
            raise SignatureRefusedError(
                _MSG_VERIFY_FAILED.format(
                    principal=principal,
                    namespace=self._config.namespace,
                    stderr=completed.stderr.decode("utf-8", "replace").strip(),
                )
            )
        stdout = completed.stdout.decode("utf-8", "replace")
        match = _FINGERPRINT_PATTERN.search(stdout)
        if match is None:
            raise SignerNotAllowedError(_MSG_NO_FINGERPRINT.format(stdout=stdout))
        return match.group(0)
