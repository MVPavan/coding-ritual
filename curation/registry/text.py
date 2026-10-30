"""Small text helpers shared by views and the CLI."""

from __future__ import annotations


def _one_line(text: str, width: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"
