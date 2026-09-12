"""Complete UTF-8 envelope limits at public loading/composition seams."""

from pathlib import Path

from workflow_interpreter.schema.loader import load_graph


def test_byte_only_graph_loads_without_obsolete_token_field(tmp_path: Path) -> None:
    original = Path("workflow_interpreter/fixtures/feature-delivery.toml").read_text()
    path = tmp_path / "bytes.toml"
    path.write_text(original.replace("token_budget", "context_budget_bytes"))
    graph = load_graph(path)
    task = next(node for node in graph.document.node if node.kind.value == "task")
    assert task.context_budget_bytes is not None
    assert task.token_budget is None


def test_full_envelope_refuses_essential_overflow(fake_store) -> None:
    import pytest

    from tests._bdio import entry_request, load_definition, make_root
    from workflow_interpreter.foreman.inputs import (
        DefaultComposer,
        InputsUnavailable,
        Materialized,
    )

    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    with pytest.raises(InputsUnavailable, match="envelope"):
        DefaultComposer().compose(root, activation, (Materialized(text="é" * 140000),))


def test_optional_trim_keeps_essential_sections_and_records_reference() -> None:
    from workflow_interpreter.foreman.envelope import EnvelopeSection, compose_envelope

    result = compose_envelope(
        "protocol",
        (
            EnvelopeSection(name="advice", text="essential advice"),
            EnvelopeSection(
                name="large",
                text="x" * 1000,
                optional=True,
                reference="git:full",
                digest="a" * 40,
            ),
        ),
        limit=240,
        reference="manifest",
    )
    assert result.included == ("advice",)
    assert result.omissions[0].reference == "git:full"
    assert result.byte_count <= 240
    assert "essential advice" in result.text


def test_utf8_exact_fit_and_one_byte_overflow() -> None:
    import pytest

    from workflow_interpreter.foreman.envelope import EnvelopeRefusal, compose_envelope

    measured = compose_envelope("é", (), limit=1000, reference="manifest")
    assert measured.byte_count == len(measured.text.encode("utf-8"))
    compose_envelope("é", (), limit=measured.byte_count, reference="manifest")
    with pytest.raises(EnvelopeRefusal):
        compose_envelope("é", (), limit=measured.byte_count - 1, reference="manifest")
