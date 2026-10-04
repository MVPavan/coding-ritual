"""The browser qualification receipt must identify its audited build base."""

from image_browser_qualification import BASE, OVERLAY


def test_browser_qualification_base_matches_dockerfile() -> None:
    base = next(
        line.removeprefix("FROM ").strip()
        for line in (OVERLAY / "Dockerfile").read_text().splitlines()
        if line.startswith("FROM ")
    )
    assert base == BASE
