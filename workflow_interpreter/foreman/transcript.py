"""Transcript shaping that bounds bytes emitted to a foreman model."""


def bounded_tail(text: str, limit: int) -> str:
    """Return a UTF-8-safe suffix whose emitted bytes are at most ``limit``."""
    if limit <= 0:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    return encoded[-limit:].decode("utf-8", errors="ignore")
