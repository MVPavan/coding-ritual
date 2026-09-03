"""Loader, canonical body and pinning tests (spec v0.3.1 §2 rule 8, §3.1).

The parse → schema → model pipeline, the `wf-canon-json/1` wire format, and the
loaders' totality over hostile input.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from tests._helpers import (
    AUTHORING_FIXTURE,
    FEATURE_DELIVERY_CONTENT_HASH,
    MINIMAL_GRAPH,
    VALID_FIXTURE,
    mutate,
    write,
)
from workflow_interpreter import (
    CANON_VERSION,
    GraphValidationError,
    RuleId,
    canonical_bytes,
    graph_schema,
    load_graph,
    load_pinned_body,
)
from workflow_interpreter.schema.loader import CANON_KEY

UNKNOWN_FIELD_CASES = (
    pytest.param(
        "[fallback]\n", "[bogus_table]\nx = 1\n\n[fallback]\n", id="depth1-root-table"
    ),
    pytest.param(
        'name = "shipped"\nkind = "terminal"\n',
        'name = "shipped"\nkind = "terminal"\nbogus_field = true\n',
        id="depth2-node-property",
    ),
    pytest.param(
        '{ cmd = "scripts/review-checks.sh",  timeout = "5m"  }',
        '{ cmd = "scripts/review-checks.sh", timeout = "5m", bogus_field = 1 }',
        id="depth3-verify-entry-property",
    ),
)

# Semantic edits to the §2 fixture; each must move the pinning hash (§2 rule 8).
HASH_SENSITIVITY_CASES = (
    pytest.param(
        (
            (
                'outcomes      = ["done", "no_diff", "fail_plan"]',
                'outcomes      = ["done", "no_diff", "fail_plan", "fail_code"]',
            ),
            (
                '[[edge]]\nfrom = "implement"\non   = "fail_plan"\nto   = "triage"\n',
                (
                    '[[edge]]\nfrom = "implement"\non   = "fail_plan"\n'
                    'to   = "triage"\n\n[[edge]]\nfrom = "implement"\n'
                    'on   = "fail_code"\nto   = "triage"\n'
                ),
            ),
        ),
        id="added-outcome-and-edge",
    ),
    pytest.param(
        (
            (
                (
                    'name          = "diff_artifact"\n'
                    'producer      = "node:implement"\noptional      = false'
                ),
                (
                    'name          = "diff_artifact"\n'
                    'producer      = "node:implement"\noptional      = true'
                ),
            ),
        ),
        id="flipped-optional",
    ),
    pytest.param(
        (("max_entries  = 3", "max_entries  = 4"),),
        id="changed-max-entries",
    ),
)


def _pretty_printed(body: bytes) -> bytes:
    """The same content, indented — semantically equal, not the canonical emission."""
    return json.dumps(json.loads(body), sort_keys=True, indent=2).encode("utf-8")


def _reordered_keys(body: bytes) -> bytes:
    """The same members, emitted in reverse key order."""
    payload = json.loads(body)
    return json.dumps(
        dict(reversed(list(payload.items()))), separators=(",", ":")
    ).encode("utf-8")


def _duplicated_key(body: bytes) -> bytes:
    """A duplicate member; JSON parsers keep the last, so the model is unchanged."""
    stamp = json.dumps({CANON_KEY: CANON_VERSION}, separators=(",", ":"))[1:-1]
    return b"{" + stamp.encode("utf-8") + b"," + body[1:]


NONCANONICAL_ENCODINGS = (
    pytest.param(lambda body: body + b"\n", id="trailing-newline"),
    pytest.param(lambda body: b" " + body, id="leading-space"),
    pytest.param(_pretty_printed, id="pretty-printed"),
    pytest.param(_reordered_keys, id="reordered-keys"),
    pytest.param(_duplicated_key, id="duplicate-key"),
)


def test_valid_fixture_loads() -> None:
    """The §2 fixture is the validator's first passing fixture."""
    graph = load_graph(VALID_FIXTURE, allow_test_flags=True)

    assert graph.document.graph.id == "feature-delivery"
    assert graph.document.graph.entry == "implement"
    assert [node.name for node in graph.document.node] == [
        "implement",
        "review",
        "ship",
        "triage",
        "shipped",
        "abandoned",
    ]
    assert graph.warnings == ()


def test_valid_fixture_content_hash_is_stable() -> None:
    """A validated graph carries the sha256 it is pinned by (§2 rule 8)."""
    graph = load_graph(VALID_FIXTURE, allow_test_flags=True)

    assert graph.content_hash == FEATURE_DELIVERY_CONTENT_HASH


def test_the_authoring_copy_is_byte_identical_to_the_library_fixture() -> None:
    """`workflows/` authors; the package ships. Nothing else keeps them equal.

    Spec §2 (`:100-102`) duplicates the canonical graph deliberately and calls
    the split temporary. `workflows/README.md` asserts the two are
    byte-identical, and until phase 5 collapses them this is the only thing
    that makes that claim true.
    """
    assert AUTHORING_FIXTURE.read_bytes() == VALID_FIXTURE.read_bytes()


def test_content_hash_ignores_formatting(tmp_path: Path) -> None:
    """The hash covers meaning, not layout: reformatting must not move it."""
    text = VALID_FIXTURE.read_text(encoding="utf-8")
    reformatted = "\n".join(
        line.split("#")[0].rstrip().replace(" = ", "=")
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    )

    path = write(tmp_path, reformatted, "reformatted.toml")

    assert (
        load_graph(path, allow_test_flags=True).content_hash
        == FEATURE_DELIVERY_CONTENT_HASH
    )


@pytest.mark.parametrize("replacements", HASH_SENSITIVITY_CASES)
def test_semantic_edits_move_the_content_hash(
    tmp_path: Path, replacements: tuple[tuple[str, str], ...]
) -> None:
    """Any semantic edit moves the pin — the per-tick re-verification rests on it (§0)."""
    text = mutate(VALID_FIXTURE.read_text(encoding="utf-8"), replacements)

    path = write(tmp_path, text, "edited.toml")

    assert (
        load_graph(path, allow_test_flags=True).content_hash
        != FEATURE_DELIVERY_CONTENT_HASH
    )


def test_canonical_body_is_version_stamped() -> None:
    """The pinned wire format names its canonicalizer (§2 'Canonical body')."""
    graph = load_graph(VALID_FIXTURE, allow_test_flags=True)

    body = json.loads(canonical_bytes(graph.document))

    assert body["canon"] == CANON_VERSION


def test_pinned_body_round_trips() -> None:
    """TOML → canonical body → loader reproduces the same graph and the same pin (§3.1)."""
    graph = load_graph(VALID_FIXTURE, allow_test_flags=True)

    body = canonical_bytes(graph.document)
    reloaded = load_pinned_body(body, allow_test_flags=True)

    assert reloaded.document == graph.document
    assert reloaded.content_hash == FEATURE_DELIVERY_CONTENT_HASH
    assert reloaded.content_hash == hashlib.sha256(body).hexdigest()
    assert canonical_bytes(reloaded.document) == body


@pytest.mark.parametrize("encode", NONCANONICAL_ENCODINGS)
def test_pinned_body_rejects_noncanonical_encodings(
    encode: Callable[[bytes], bytes],
) -> None:
    """A pin is a statement about bytes: an equivalent re-encoding is refused (§2 rule 8).

    Never normalized — accepting it would make `content_hash` a property of the
    re-parsed model rather than of the bytes bd carries (invariant 9).
    """
    body = canonical_bytes(load_graph(VALID_FIXTURE, allow_test_flags=True).document)
    supplied = encode(body)
    assert supplied != body

    with pytest.raises(GraphValidationError) as excinfo:
        load_pinned_body(supplied, allow_test_flags=True)

    assert excinfo.value.rule_ids == frozenset({RuleId.PINNED_NONCANONICAL})


def test_pinned_body_rejects_truncation() -> None:
    """A corrupted body is a finding, not a stray JSONDecodeError."""
    body = canonical_bytes(load_graph(VALID_FIXTURE, allow_test_flags=True).document)

    with pytest.raises(GraphValidationError) as excinfo:
        load_pinned_body(body[: len(body) // 2], allow_test_flags=True)

    assert excinfo.value.rule_ids == frozenset({RuleId.PINNED_PARSE})


def test_pinned_body_requires_the_canon_stamp() -> None:
    """An unstamped body is not a `wf-canon-json/1` pinned body."""
    graph = load_graph(VALID_FIXTURE, allow_test_flags=True)
    body = json.loads(canonical_bytes(graph.document))
    del body["canon"]

    with pytest.raises(GraphValidationError) as excinfo:
        load_pinned_body(json.dumps(body).encode("utf-8"), allow_test_flags=True)

    assert excinfo.value.rule_ids == frozenset({RuleId.SCHEMA})


def test_pinned_body_byte_flip_moves_the_hash() -> None:
    """A body edited in place no longer hashes to its pin (§0 per-tick verification)."""
    graph = load_graph(VALID_FIXTURE, allow_test_flags=True)
    body = canonical_bytes(graph.document)
    corrupted = body.replace(
        b'"max_total_activations":20', b'"max_total_activations":21'
    )
    assert corrupted != body

    reloaded = load_pinned_body(corrupted, allow_test_flags=True)

    assert reloaded.content_hash != graph.content_hash


def test_authored_toml_may_not_carry_the_canon_stamp(tmp_path: Path) -> None:
    """The canon member belongs to the pinned path only; TOML declaring it is unknown-field."""
    path = write(tmp_path, f'canon = "{CANON_VERSION}"\n{MINIMAL_GRAPH}')

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({RuleId.SCHEMA})


@pytest.mark.parametrize(("original", "replacement"), UNKNOWN_FIELD_CASES)
def test_unknown_fields_are_rejected(
    tmp_path: Path, original: str, replacement: str
) -> None:
    """Reject-unknown holds at every nesting level, one finding per unknown key (P2)."""
    text = mutate(VALID_FIXTURE.read_text(encoding="utf-8"), ((original, replacement),))

    path = write(tmp_path, text, "unknown.toml")

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path, allow_test_flags=True)

    assert excinfo.value.rule_ids == frozenset({RuleId.SCHEMA})
    assert len([f for f in excinfo.value.findings if "bogus" in f.message]) == 1


def test_malformed_toml_is_reported_as_a_finding(tmp_path: Path) -> None:
    """A parse failure is a finding, not a stray TOMLDecodeError."""
    path = write(tmp_path, "[graph\nid = 'x'\n", "broken.toml")

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({RuleId.TOML_PARSE})


def test_binary_file_is_reported_as_a_finding(tmp_path: Path) -> None:
    """Non-UTF-8 bytes are a finding, not a stray UnicodeDecodeError (r3 probe)."""
    path = tmp_path / "binary.toml"
    path.write_bytes(bytes(range(256)) * 8)

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({RuleId.TOML_PARSE})


def test_pinned_body_with_an_oversized_integer_is_a_finding() -> None:
    """CPython's int/str conversion limit is a finding, not a stray ValueError (r3 probe)."""
    body = b'{"canon":"wf-canon-json/1","instance":' + b"9" * 5000 + b"}"

    with pytest.raises(GraphValidationError) as excinfo:
        load_pinned_body(body)

    assert excinfo.value.rule_ids == frozenset({RuleId.PINNED_PARSE})


def test_deeply_nested_pinned_body_is_a_finding() -> None:
    """Nesting past the recursion limit is a finding, not a stray RecursionError (r3 probe)."""
    depth = 200_000
    body = b"[" * depth + b"]" * depth

    with pytest.raises(GraphValidationError) as excinfo:
        load_pinned_body(body)

    assert excinfo.value.rule_ids == frozenset({RuleId.PINNED_PARSE})


def test_schema_errors_are_reported_together(tmp_path: Path) -> None:
    """The loader reports all schema errors, not the first (brief §1)."""
    path = write(tmp_path, "", "empty.toml")

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({RuleId.SCHEMA})
    missing = {
        re.sub(r".*'(\w+)' is a required property.*", r"\1", finding.message)
        for finding in excinfo.value.findings
    }
    assert missing == {"graph", "instance", "node", "edge", "fallback"}


def test_schema_stage_precedes_the_semantic_stage(tmp_path: Path) -> None:
    """A schema defect is reported alone; semantic rules never run on rejected input."""
    text = mutate(
        MINIMAL_GRAPH,
        (
            ('version = "1.0.0"', 'version = "not-a-semver"'),
            ("max_total_activations = 5", "max_total_activations = 0"),
        ),
    )

    path = write(tmp_path, text)

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({RuleId.SCHEMA})


def test_graph_schema_is_a_defensive_copy() -> None:
    """A caller mutating the returned schema cannot corrupt later validations."""
    schema = graph_schema()
    schema["properties"].clear()

    assert graph_schema()["properties"]["graph"]


def test_schema_description_warns_that_it_is_not_sufficient() -> None:
    """Schema-alone consumers must be told the per-kind checks live elsewhere."""
    description = graph_schema()["description"]

    assert "NOT sufficient" in description
    assert "validator" in description
