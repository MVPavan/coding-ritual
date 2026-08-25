"""Validating loader for workflow graph definitions (spec v0.3.1 §2).

Pipeline: parse (`tomllib` for authored TOML, `json` for a pinned body) → JSON
Schema (all errors, not the first) → pydantic → semantic rules →
`GraphDefinition` with the pinning hash. Every stage that fails raises
`GraphValidationError` carrying all ERRORS of that stage; a later stage never
runs on input an earlier one rejected.

TOML is authoring syntax only. The pinned wire format is `wf-canon-json/1`:
the canonical JSON emission of the resolved model, stamped with its
canonicalizer version; `load_pinned_body` reads exactly those bytes back
through the same validation pipeline (§2 'Canonical body', §3.1).
"""

from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from workflow_interpreter.schema.models import (
    Finding,
    GraphDefinition,
    GraphDocument,
    RuleId,
    Severity,
)
from workflow_interpreter.schema.validator import validate_semantics

SCHEMA_FILE: Final[str] = "graph_schema.json"
CANON_KEY: Final[str] = "canon"
CANON_VERSION: Final[str] = "wf-canon-json/1"
PINNED_SOURCE: Final[str] = "<pinned body>"
_ROOT_LOCATION: Final[str] = "$"
_MSG_TOML_PARSE: Final[str] = (
    "file could not be read as a TOML graph document: {reason}"
)
_MSG_PINNED_PARSE: Final[str] = "pinned body is not valid {canon} JSON: {reason}"
_MSG_PINNED_NOT_OBJECT: Final[str] = "pinned body is not a JSON object"
_MSG_PINNED_NONCANONICAL: Final[str] = (
    "pinned body is not the canonical {canon} emission of its own content; "
    "a semantically equivalent but non-canonical encoding (whitespace, key "
    "order, duplicate keys) is rejected, never normalized (§2 rule 8)"
)
_BOUNDARY_FAILURES: Final[tuple[type[Exception], ...]] = (
    # `ValueError` covers `tomllib.TOMLDecodeError`, `json.JSONDecodeError`,
    # `UnicodeDecodeError` and CPython's int/str conversion limit; a deeply
    # nested body instead exhausts the stack, and `RecursionError` is not a
    # `ValueError`. Both public loaders must be total over their input, so the
    # whole pipeline runs inside this guard, not just the parse call.
    ValueError,
    RecursionError,
)
_ERROR_SUMMARY: Final[str] = "{source}: {count} validation finding(s)\n{details}"
_FINDING_LINE: Final[str] = "  [{severity}] {rule} at {location}: {message}"


class GraphValidationError(Exception):
    """Raised when a graph definition is rejected; carries every error finding.

    `findings` holds ERRORS only — a warning never blocks a load, so it never
    appears here; warnings observed before the failure are kept separately.
    """

    def __init__(
        self,
        source: Path | str,
        findings: tuple[Finding, ...],
        warnings: tuple[Finding, ...] = (),
    ) -> None:
        self.source = source
        self.findings = findings
        self.warnings = warnings
        details = "\n".join(
            _FINDING_LINE.format(
                severity=finding.severity.value,
                rule=finding.rule.value,
                location=finding.location,
                message=finding.message,
            )
            for finding in findings
        )
        super().__init__(
            _ERROR_SUMMARY.format(source=source, count=len(findings), details=details)
        )

    @property
    def rule_ids(self) -> frozenset[RuleId]:
        """The distinct rules that produced the error findings."""
        return frozenset(finding.rule for finding in self.findings)


@cache
def _cached_schema() -> dict[str, Any]:
    """Parse the packaged schema once; callers never see this instance."""
    text = (
        resources.files(__package__).joinpath(SCHEMA_FILE).read_text(encoding="utf-8")
    )
    schema: dict[str, Any] = json.loads(text)
    return schema


def graph_schema() -> dict[str, Any]:
    """The JSON Schema the parsed structure is validated against.

    A deep copy: the schema is process-wide state and a caller mutating it
    would corrupt every later validation.
    """
    return copy.deepcopy(_cached_schema())


@cache
def _pinned_schema() -> dict[str, Any]:
    """The graph schema extended with the required `canon` stamp.

    Only the pinned-body path accepts this member; authored TOML declaring it
    stays an unknown-property error.
    """
    schema = copy.deepcopy(_cached_schema())
    schema["properties"][CANON_KEY] = {"const": CANON_VERSION}
    schema["required"] = [*schema["required"], CANON_KEY]
    return schema


def canonical_bytes(document: GraphDocument) -> bytes:
    """The `wf-canon-json/1` pinned body — the pre-image of `content_hash`.

    Canonical JSON over the resolved model (sorted keys, aliases, nulls
    elided) stamped with the canonicalizer version, so reformatting the
    authored TOML does not move the hash while any semantic edit does, and a
    future canonicalizer is distinguishable from this one (§2 rule 8).
    """
    payload = document.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload[CANON_KEY] = CANON_VERSION
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def content_hash(document: GraphDocument) -> str:
    """sha256 over `canonical_bytes`, used to pin the graph into bd (§3.1)."""
    return hashlib.sha256(canonical_bytes(document)).hexdigest()


def _json_path(parts: tuple[str | int, ...]) -> str:
    """Render a pydantic error location in the `$.node[0].name` dialect."""
    rendered = _ROOT_LOCATION
    for part in parts:
        rendered += f"[{part}]" if isinstance(part, int) else f".{part}"
    return rendered


def _schema_findings(data: dict[str, Any], schema: dict[str, Any]) -> list[Finding]:
    """Every JSON Schema violation, ordered by location, as findings."""
    validator = Draft202012Validator(schema)
    findings = [
        Finding(
            rule=RuleId.SCHEMA,
            severity=Severity.ERROR,
            location=error.json_path,
            message=error.message,
        )
        for error in validator.iter_errors(data)
    ]
    return sorted(findings, key=lambda finding: (finding.location, finding.message))


def _model_findings(error: ValidationError) -> list[Finding]:
    """Every pydantic violation as a finding in the shared location dialect."""
    return [
        Finding(
            rule=RuleId.SCHEMA,
            severity=Severity.ERROR,
            location=_json_path(tuple(detail["loc"])),
            message=detail["msg"],
        )
        for detail in error.errors()
    ]


def _validate(
    data: dict[str, Any],
    schema: dict[str, Any],
    source: Path | str,
    *,
    allow_test_flags: bool,
) -> GraphDefinition:
    """Run schema, model and semantic validation over a parsed document."""
    schema_findings = _schema_findings(data, schema)
    if schema_findings:
        raise GraphValidationError(source, tuple(schema_findings))

    # The canon stamp is a property of the wire format, not of the graph.
    body = {key: value for key, value in data.items() if key != CANON_KEY}
    try:
        document = GraphDocument.model_validate(body)
    except ValidationError as exc:
        raise GraphValidationError(source, tuple(_model_findings(exc))) from exc

    findings = validate_semantics(document, allow_test_flags=allow_test_flags)
    errors = tuple(
        finding for finding in findings if finding.severity is Severity.ERROR
    )
    warnings = tuple(
        finding for finding in findings if finding.severity is Severity.WARNING
    )
    if errors:
        raise GraphValidationError(source, errors, warnings)

    return GraphDefinition(
        document=document,
        content_hash=content_hash(document),
        warnings=warnings,
    )


def _parse_error(
    source: Path | str, rule: RuleId, message: str
) -> GraphValidationError:
    """A single-finding rejection for input the pipeline cannot even read."""
    return GraphValidationError(
        source,
        (
            Finding(
                rule=rule,
                severity=Severity.ERROR,
                location=_ROOT_LOCATION,
                message=message,
            ),
        ),
    )


def load_graph(path: Path, *, allow_test_flags: bool = False) -> GraphDefinition:
    """Load, validate and hash an authored TOML graph definition.

    `allow_test_flags` opts into the §13 test switches; without it a graph
    setting `test_force_first_reject` is refused.

    Total over its input: hostile bytes leave through `GraphValidationError`,
    never as a raw traceback from a parser (see `_BOUNDARY_FAILURES`).
    """
    try:
        with path.open("rb") as handle:
            data: dict[str, Any] = tomllib.load(handle)
        return _validate(data, graph_schema(), path, allow_test_flags=allow_test_flags)
    except _BOUNDARY_FAILURES as exc:
        raise _parse_error(
            path, RuleId.TOML_PARSE, _MSG_TOML_PARSE.format(reason=exc)
        ) from exc


def load_pinned_body(data: bytes, *, allow_test_flags: bool = False) -> GraphDefinition:
    """Load a pinned `wf-canon-json/1` body through the same validation pipeline.

    The bytes must be exactly what `canonical_bytes` would emit for the
    document they encode: after the full pipeline the supplied bytes are
    compared against the canonical re-emission and refused when they differ, so
    a re-encoding cannot be laundered into a valid pin (§2 rule 8, invariant 9).
    `content_hash` is sha256 over the SUPPLIED bytes — the pin is a statement
    about the bytes carried in bd, not about a model reconstructed from them.

    Total over its input, like `load_graph` (see `_BOUNDARY_FAILURES`).
    """
    try:
        payload = json.loads(data)

        if not isinstance(payload, dict):
            raise _parse_error(
                PINNED_SOURCE, RuleId.PINNED_PARSE, _MSG_PINNED_NOT_OBJECT
            )

        body: dict[str, Any] = payload
        definition = _validate(
            body,
            _pinned_schema(),
            PINNED_SOURCE,
            allow_test_flags=allow_test_flags,
        )
        canonical = canonical_bytes(definition.document)
    except _BOUNDARY_FAILURES as exc:
        raise _parse_error(
            PINNED_SOURCE,
            RuleId.PINNED_PARSE,
            _MSG_PINNED_PARSE.format(canon=CANON_VERSION, reason=exc),
        ) from exc

    if data != canonical:
        raise GraphValidationError(
            PINNED_SOURCE,
            (
                Finding(
                    rule=RuleId.PINNED_NONCANONICAL,
                    severity=Severity.ERROR,
                    location=_ROOT_LOCATION,
                    message=_MSG_PINNED_NONCANONICAL.format(canon=CANON_VERSION),
                ),
            ),
            definition.warnings,
        )

    return GraphDefinition(
        document=definition.document,
        content_hash=hashlib.sha256(data).hexdigest(),
        warnings=definition.warnings,
    )
