"""Qualification of QMD 2.8.3's real lexical CLI lifecycle.

Only collection registration, status, lexical search, get, and update appear
here.  The test deliberately excludes QMD query, vector search, embedding,
reranking, MCP, and model download commands.
"""

from __future__ import annotations

import selectors
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from qmd_qualification import (
    PROCESS_TIMEOUT_SECONDS,
    QmdState,
    assert_empty_model_cache,
    json_output,
    new_state,
    run,
    start,
)

COLLECTION = "lexical"
NEEDLE = "cobaltlexicalneedle"
RETAINED_TEXT = "Retained text is available through QMD get."

pytestmark = pytest.mark.qmd


@pytest.fixture
def qmd_state(tmp_path: Path) -> Iterator[QmdState]:
    """Register a fresh generated Markdown collection in an isolated QMD state."""
    state = new_state(tmp_path)
    (state.corpus / "retained.md").write_text(
        f"# Retained note\n\n{NEEDLE} appears here.\n\n{RETAINED_TEXT}\n",
        encoding="utf-8",
    )
    (state.corpus / "other.md").write_text(
        "# Other note\n\nNot the target.\n",
        encoding="utf-8",
    )
    run(state, "collection", "add", str(state.corpus), "--name", COLLECTION)
    run(state, "status")
    run(state, "update")
    yield state


def search(state: QmdState, phrase: str) -> list[dict[str, object]]:
    """Return lexical JSON search data from QMD's model-free search command."""
    output = json_output(run(state, "search", phrase, "--json", "-c", COLLECTION))
    assert isinstance(output, list)
    assert all(isinstance(entry, dict) for entry in output)
    return [entry for entry in output if isinstance(entry, dict)]


def matching_paths(results: list[dict[str, object]]) -> set[str]:
    """Extract reported QMD paths while retaining a direct assertion on CLI JSON fields."""
    paths = {entry["file"] for entry in results if isinstance(entry.get("file"), str)}
    assert paths
    return {str(path) for path in paths}


def test_cold_registration_status_search_and_get_are_model_free(qmd_state: QmdState) -> None:
    """Cold state registers, indexes, searches JSON, and retains document text."""
    matches = matching_paths(search(qmd_state, NEEDLE))
    assert f"qmd://{COLLECTION}/retained.md" in matches

    fetched = run(qmd_state, "get", f"qmd://{COLLECTION}/retained.md")
    assert RETAINED_TEXT in fetched.stdout
    assert_empty_model_cache(qmd_state)


def test_update_reflects_changed_and_new_markdown_without_mtime_assumptions(
    qmd_state: QmdState,
) -> None:
    """Update must reflect content changes and a newly created Markdown file."""
    (qmd_state.corpus / "retained.md").write_text(
        "# Retained replacement\n\namberlexicalneedle replaced the original.\n",
        encoding="utf-8",
    )
    (qmd_state.corpus / "new.md").write_text(
        "# New note\n\nverdantlexicalneedle is newly indexed.\n",
        encoding="utf-8",
    )
    run(qmd_state, "update")

    amber_paths = matching_paths(search(qmd_state, "amberlexicalneedle"))
    verdant_paths = matching_paths(search(qmd_state, "verdantlexicalneedle"))
    assert f"qmd://{COLLECTION}/retained.md" in amber_paths
    assert f"qmd://{COLLECTION}/new.md" in verdant_paths
    assert search(qmd_state, NEEDLE) == []


def test_two_independent_lexical_startups_share_one_isolated_database(
    qmd_state: QmdState,
) -> None:
    """Two independently started lexical CLI processes produce valid matching JSON."""
    barrier = threading.Barrier(3)
    results: list[subprocess.CompletedProcess[str] | None] = [None, None]

    def worker(position: int) -> None:
        barrier.wait(timeout=PROCESS_TIMEOUT_SECONDS)
        results[position] = run(qmd_state, "search", NEEDLE, "--json", "-c", COLLECTION)

    threads = [threading.Thread(target=worker, args=(position,)) for position in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait(timeout=PROCESS_TIMEOUT_SECONDS)
    for thread in threads:
        thread.join(timeout=PROCESS_TIMEOUT_SECONDS)
        assert not thread.is_alive(), "concurrent lexical startup exceeded its deadline"

    for result in results:
        assert result is not None
        parsed = json_output(result)
        assert isinstance(parsed, list)
        assert all(isinstance(entry, dict) for entry in parsed)
        paths = matching_paths([entry for entry in parsed if isinstance(entry, dict)])
        assert f"qmd://{COLLECTION}/retained.md" in paths


def test_interrupted_update_recovers_after_observable_execution(qmd_state: QmdState) -> None:
    """Kill an update only after it reports execution, then recover search/get."""
    for position in range(80):
        content = (
            f"# Bulk {position}\n\ninterruptiblelexicalneedle {position}\n"
            + ("payload " * 1200)
        )
        (qmd_state.corpus / f"bulk-{position}.md").write_text(
            content,
            encoding="utf-8",
        )

    process = start(qmd_state, "update")
    observed_output = ""
    try:
        assert process.stdout is not None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            events = selector.select(PROCESS_TIMEOUT_SECONDS)
        assert events, "QMD update produced no observable execution output before its deadline"
        observed_output = process.stdout.readline()
        assert observed_output.strip(), "QMD update output was empty before interruption"
        assert process.poll() is None, (
            "QMD update completed before an in-flight interruption was possible"
        )
        process.kill()
        process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=PROCESS_TIMEOUT_SECONDS)

    assert observed_output
    run(qmd_state, "update")
    assert f"qmd://{COLLECTION}/bulk-0.md" in matching_paths(
        search(qmd_state, "interruptiblelexicalneedle")
    )
    fetched = run(qmd_state, "get", f"qmd://{COLLECTION}/retained.md")
    assert RETAINED_TEXT in fetched.stdout
