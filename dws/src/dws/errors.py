"""Public failures with bounded, actionable messages."""

from __future__ import annotations


class DWSError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.source_status: int | None = None
        self.target_status: int | None = None
        self.escalation: dict[str, str | int] | None = None
        self.engine_path: dict[str, object] | None = None

    def payload(self) -> dict[str, object]:
        error: dict[str, object] = {"code": self.code, "message": self.message}
        if self.escalation is not None:
            error["escalation"] = self.escalation
        if self.engine_path is not None:
            error["engine_path"] = self.engine_path
        return {"error": error}
