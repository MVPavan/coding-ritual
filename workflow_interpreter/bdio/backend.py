"""The store's backend seam — what a `WorkflowStore` is built on (§3.1, §3.2).

One backend is pinned per root at creation and never changes, so the store a
root is read and written through has to be chosen BEFORE the root is loaded.
That choice is a `BackendLocator`'s answer and a `StoreBackendFactory`'s
construction; nothing above the seam names a transport class.

`bd` is the only backend today, and `BdClient` is its only implementation of
`StoreBackend` — the protocol exists so that the store, and every collaborator
the store hands its backend to, is typed against the surface rather than
against bd.
"""

from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.errors import StoreConfigError
from workflow_interpreter.bdio.records import CanaryResult
from workflow_interpreter.bdio.rows import (
    BackendIdentity,
    GateClosure,
    NewRow,
    RowGuard,
    RowQuery,
    StoreRow,
)
from workflow_interpreter.bdio.wire import Metadata

_MSG_UNSUPPORTED: Final[str] = (
    "no backend is configured for {requested!r}; this process was built on {pinned!r}"
)
_MSG_NOT_BUILT: Final[str] = (
    "no backend is configured for {requested!r}; this process was built with "
    "{available}"
)


class StoreBackend(Protocol):
    """The durable-row surface a `WorkflowStore` and its collaborators use.

    Every type here is backend-neutral (`bdio/rows.py`): a backend is a place
    rows live, not a bd workspace. The write methods are package-private in
    the implementation and stay that way here — the typed operations in this
    package are the only callers (§0.1).
    """

    @property
    def kind(self) -> BackendKind:
        """Which backend this transport speaks for."""

    def identity(self) -> BackendIdentity:
        """Where this backend's rows and their execution locks live (§3.4)."""

    def probe(self) -> CanaryResult:
        """Assert this is the pinned store and round-trip a carrier (§11).

        The assertions are the backend's own: what identity means to bd is a
        `bd context` field set, and what it means to the ledger is a schema
        version and a pinned wrapper root. A caller gets the evidence, never
        the vocabulary.
        """

    def get_row(self, row_id: str) -> StoreRow:
        """One row by id — the read-back path for every write."""

    def find_rows(self, query: RowQuery) -> tuple[StoreRow, ...]:
        """Rows the query selects, closed rows included."""

    def _create_row(self, new: NewRow) -> StoreRow:
        """Create a row and verify it read back exactly as written."""

    def _merge_metadata(
        self, row_id: str, metadata: Metadata, *, guard: RowGuard | None = None
    ) -> StoreRow:
        """Merge metadata into a row and verify the merged result.

        `guard` is re-checked against the row this write is about to change,
        by a backend that can hold that read and this write in one
        transaction; see `RowGuard` for what a backend without transactions
        does instead.
        """

    def _claim_and_merge_metadata(self, row_id: str, metadata: Metadata) -> StoreRow:
        """Claim a row and merge metadata in one operation."""

    def _close_row(self, row_id: str, reason: str) -> StoreRow:
        """Close a row with a structured reason and verify both landed."""

    def _close_gate(self, closure: GateClosure) -> StoreRow:
        """Take a gate's decision whole: nonce, state, outcome, signature (§3.3).

        One method rather than four calls because the operation is atomic
        where it can be. A backend that cannot transact performs the same
        writes in the §5.1 order — carrier first, close second — which is what
        makes a crash between them repairable forward.
        """


class StoreBackendFactory(Protocol):
    """Builds the backend a pinned `BackendKind` names."""

    def __call__(self, backend: BackendKind) -> StoreBackend:
        """The backend for `backend`, or `StoreConfigError` if none is configured."""


class BackendLocator(Protocol):
    """Answers which backend owns a root, before the root is loaded (§3.2)."""

    def __call__(self, root_id: str) -> BackendKind:
        """The backend pinned for this root."""


@runtime_checkable
class PinnableBackendLocator(Protocol):
    """A locator that can be TOLD a pin it could not read for itself (§3.2).

    The bridge record names the backend of an attempt root before that root
    exists, and for a bd-backed attempt of a ledger-pinned task nothing durable
    says so afterwards: the ledger holds no row for a bd root, and the `tasks`
    row still names the first attempt's backend. So the answer has to be
    installed at creation, by the one caller that holds the record.

    Runtime-checkable because the default locator is a plain function with
    nothing to install (bd is its answer for every root), and a composition
    wired that way must keep working rather than grow a no-op pin.
    """

    def __call__(self, root_id: str) -> BackendKind:
        """The backend pinned for this root."""

    def pin(self, root_id: str, backend: BackendKind) -> None:
        """Record the backend a root was created on."""


class PinnedBackendFactory:
    """The single-backend factory: one transport, and a refusal for the rest.

    A process holds one transport per backend, so the factory hands out the
    one it was built with rather than constructing a second connection per
    root. Asking for a backend this process was not built on is a refusal, not
    a silent fallback to the one it has.
    """

    def __init__(self, backend: StoreBackend) -> None:
        self._backend = backend

    def __call__(self, backend: BackendKind) -> StoreBackend:
        """The pinned backend, or a refusal naming both kinds."""
        if backend is not self._backend.kind:
            raise StoreConfigError(
                _MSG_UNSUPPORTED.format(
                    requested=backend.value, pinned=self._backend.kind.value
                )
            )
        return self._backend


class SelectableBackendFactory:
    """The two-backend factory: one transport per kind, and no substitutions.

    A cutover process holds BOTH — a bd transport for bd-pinned roots, the
    task bead and the claims D20 keeps in bd, and a ledger transport for
    ledger-pinned ones — and hands out whichever the located pin names. A kind
    this process was not built with is a refusal naming what it does have,
    never the other transport: a root read from the wrong store looks missing,
    not broken.
    """

    def __init__(self, *backends: StoreBackend) -> None:
        self._backends: dict[BackendKind, StoreBackend] = {
            backend.kind: backend for backend in backends
        }

    def __call__(self, backend: BackendKind) -> StoreBackend:
        """The transport for `backend`, or a refusal naming the ones built."""
        found = self._backends.get(backend)
        if found is None:
            raise StoreConfigError(
                _MSG_NOT_BUILT.format(
                    requested=backend.value,
                    available=", ".join(sorted(kind.value for kind in self._backends))
                    or "no backend",
                )
            )
        return found


def bd_backend(root_id: str) -> BackendKind:
    """Locate a root's backend while bd is the only one there is.

    §3.2 moves this to the bridge record's `root_backend` and the ledger
    `tasks` row; until a second backend exists there is nothing to read, and
    reading bd to find out that the answer is bd would cost a round-trip per
    tick.
    """
    return BackendKind.BD
