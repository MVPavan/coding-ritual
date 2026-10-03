"""Public failures with bounded, actionable messages."""

from __future__ import annotations


class DWSError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

    def payload(self) -> dict[str, object]:
        return {"error": {"code": self.code, "message": self.message}}
