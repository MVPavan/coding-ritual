"""Process-local ownership of RPC descriptors across the existing fork barrier."""

import os
from typing import Final

MSG_PIPES_TAKEN: Final[str] = "RPC pipe endpoints already transferred"


class RpcPipes:
    """Own parent endpoints until transferred exactly once to the RPC client."""

    def __init__(self) -> None:
        self._stdin_read, self._stdin_write = os.pipe()
        self._stdout_read, self._stdout_write = os.pipe()
        self._stderr_read, self._stderr_write = os.pipe()
        self._owned = {
            self._stdin_read,
            self._stdin_write,
            self._stdout_read,
            self._stdout_write,
            self._stderr_read,
            self._stderr_write,
        }
        self._taken = False

    def child_setup(self) -> None:
        """Attach only the child half; no host descriptors survive exec."""
        os.dup2(self._stdin_read, 0)
        os.dup2(self._stdout_write, 1)
        os.dup2(self._stderr_write, 2)
        self.close()

    def parent_setup(self) -> None:
        """Close child endpoints immediately after fork in the parent."""
        for descriptor in (self._stdin_read, self._stdout_write, self._stderr_write):
            os.close(descriptor)
            self._owned.remove(descriptor)

    def detach(self) -> tuple[int, int, int]:
        """Transfer the three parent descriptors to their sole resident owner."""
        if self._taken:
            raise RuntimeError(MSG_PIPES_TAKEN)
        self._taken = True
        result = (self._stdin_write, self._stdout_read, self._stderr_read)
        self._owned.difference_update(result)
        return result

    def close(self) -> None:
        """Close only endpoints still owned here, including failed-launch cleanup."""
        for descriptor in self._owned:
            os.close(descriptor)
        self._owned.clear()
