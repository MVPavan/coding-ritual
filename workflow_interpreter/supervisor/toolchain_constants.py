"""Toolchain filesystem layout, environment keys, and preparation diagnostics."""

from typing import Final

CACHE: Final[str] = "uv-cache"
PYTHON: Final[str] = "python"
TOOLCHAIN: Final[str] = "toolchain"
MANIFEST: Final[str] = "seed.json"
PREPARED: Final[str] = "toolchain-seed.json"
STAGING_PREFIX: Final[str] = ".toolchain-"
PROBE_PREFIX: Final[str] = ".probe-"
SEED_DIRECTORY: Final[str] = "toolchain-seeds"
LOCK_FILE: Final[str] = "uv.lock"
PROJECT_FILE: Final[str] = "pyproject.toml"
PYTHON_FILE: Final[str] = ".python-version"
WHEELS: Final[str] = "wheels-v5"
ARCHIVES: Final[str] = "archive-v0"
PYPI: Final[str] = "pypi"
INDEX: Final[str] = "index"
ENV_CACHE: Final[str] = "UV_CACHE_DIR"
ENV_VENV: Final[str] = "UV_PROJECT_ENVIRONMENT"
ENV_PYTHON: Final[str] = "UV_PYTHON_INSTALL_DIR"
ENV_OFFLINE: Final[str] = "UV_OFFLINE"
ENV_DOWNLOADS: Final[str] = "UV_PYTHON_DOWNLOADS"
ENV_LINK_MODE: Final[str] = "UV_LINK_MODE"
ENV_NO_CONFIG: Final[str] = "UV_NO_CONFIG"
ENV_NO_SYNC: Final[str] = "UV_NO_SYNC"
MSG_ACTIVATION_LINK: Final[str] = "activation toolchain path contains a symlink"
MSG_OUTSIDE_WRAPPER: Final[str] = "activation cache is outside wrapper root"
MSG_NO_PROJECT: Final[str] = "uv.lock requires admitted pyproject.toml"
MSG_RELATIVE_HOST: Final[str] = "uv returned a relative host path"
MSG_UNMANAGED: Final[str] = "uv selected a non-managed interpreter"
MSG_TAINTED: Final[str] = "launched private cache cannot be host-probed"
MSG_PRIVATE_LINK: Final[str] = "private toolchain path contains a symlink"
MSG_PRIVATE_ROOT_LINK: Final[str] = "private toolchain is a symlink"
MSG_INTERRUPTED_LINK: Final[str] = "interrupted toolchain path is a symlink"
MSG_NO_BASE: Final[str] = "uv project requires an admitted base commit"
MSG_SOURCE_LINK: Final[str] = "toolchain source path contains a symlink"
MSG_HOST_OVERLAP: Final[str] = "overlapping host toolchain roots"
MSG_RECEIPT_PATH: Final[str] = "private seed receipt path mismatch"
MSG_SEED_LINK: Final[str] = "interrupted seed path is a symlink"
MSG_OVERLAP: Final[str] = "overlapping toolchain source and destination"
MSG_LOCK_TIMEOUT: Final[str] = "toolchain preparation lock timed out"
MSG_COPY: Final[str] = "private toolchain copy failed"
MSG_DISK: Final[str] = "insufficient free space for private toolchain"
MSG_BOUNDS: Final[str] = "toolchain copy exceeds configured bounds"
MSG_INDEX_BOUND: Final[str] = "host wheel index exceeds entry bound"
MSG_ARCHIVE_LINK: Final[str] = "host wheel link escapes archive cache"
MSG_WHEEL_ENTRY: Final[str] = "unsupported host wheel index entry"
MSG_WHEEL_BOUND: Final[str] = "host wheel metadata exceeds byte bound"
MSG_CLEANUP_LINK: Final[str] = "private toolchain cleanup path contains a symlink"
MSG_NO_IDENTITY: Final[str] = (
    "private toolchain retained: launched runner identity missing"
)
MSG_NOT_DEAD: Final[str] = "private toolchain retained: runner death is unproven"
MSG_HOST_ABSOLUTE: Final[str] = "toolchain host paths must be absolute"
MSG_DUPLICATE_PROJECTS: Final[str] = "duplicate toolchain projects"
MSG_PROJECT_RELATIVE: Final[str] = "toolchain projects must be repo-relative"
MSG_COMMAND: Final[str] = "toolchain {operation} failed (exit {exit_code}): {text}"
MSG_PREPARATION: Final[str] = "toolchain preparation failed: {error}"
MSG_PIN_LINK: Final[str] = "toolchain pin contains symlink: {path}"
MSG_PIN_SIZE: Final[str] = "toolchain pin exceeds size bound: {path}"
MSG_PIN_CHANGED: Final[str] = (
    "dependency pin changed: {path}; admit updated dependencies first"
)
MSG_PIN_REGULAR: Final[str] = "toolchain pin must be a regular file: {path}"
MSG_ESCAPE: Final[str] = "escaping toolchain link: {path}"
MSG_SPECIAL: Final[str] = "special toolchain file: {path}"
MSG_CLEANUP: Final[str] = "toolchain cleanup: {error}"
LOG_CLEANUP: Final[str] = "wf.toolchain.cleanup_failed"

HOST_ENV_KEYS: Final[tuple[str, ...]] = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
)
CLEANUP_PENDING: Final[str] = "toolchain-cleanup.json"

PYTHON_REQUEST_MAX_LENGTH: Final[int] = 128
_PYTHON_VERSION: Final[str] = r"[0-9]+(?:\.[0-9]+){0,2}"
_PYTHON_SPECIFIER: Final[str] = r"(?:===|==|!=|~=|<=|>=|<|>) *" + _PYTHON_VERSION
PYTHON_REQUEST_PATTERN: Final[str] = (
    r"(?:cpython@|python)?(?:"
    + _PYTHON_VERSION
    + "|"
    + _PYTHON_SPECIFIER
    + r"(?: *, *"
    + _PYTHON_SPECIFIER
    + r")*)"
)
MSG_PYTHON_REQUEST: Final[str] = (
    "invalid Python request: use a version or numeric version specifier "
    f"of at most {PYTHON_REQUEST_MAX_LENGTH} characters"
)
