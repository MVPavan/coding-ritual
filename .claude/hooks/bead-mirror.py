#!/usr/bin/env python3
"""bead-mirror: mirror enrolled Beads beads to GitHub issues, from one writer clone.

Standard library only; runs under any Python 3.9+. Nothing here is specific to one
project: everything it needs comes from the writer switch, a JSON file the owner
writes in ``<git common dir>/bead-mirror/switch.json``. Without that file every
subcommand exits 0, prints nothing and creates nothing.

Before any write the command checks that the Beads store (resolved by running ``bd``
at the clone's top level with every ``BEADS_*`` override removed) has the switch's
``project_id``, that the ``gh`` login is the switch's account, that the repository at
the recorded name has the recorded node ID, and that the state file is bound to the
same store, repository and account. Every ``gh`` call names the switch's host, and
every GitHub write is a GraphQL mutation addressed by node ID.

Exit codes: 0 done (holds are reported on stdout, not failures); 2 usage; 3 switch
invalid; 4 an authority check failed (report on stderr; state mismatches persist until
``reset-state``); 5 GitHub unavailable (``gh`` missing, unauthenticated, rate-limited,
offline or failing, or the issues listing incomplete; also when that happens late in a
run, which keeps what it already recorded and leaves the rest pending); 6 Beads
unavailable; 7 busy
(another run holds the clone-wide lock past the wait bound); 8 not implemented;
9 refused (the ``pr`` path, ``link`` or ``resolve`` declined, with the reason).

The banner. Every issue body starts with two lines::

    <!-- bead-mirror v1 store=<store project_id> bead=<bead id> -->
    > Generated from bead `<bead id>` in Beads. ...comment instead of editing...

The first line is the machine-readable one and is parsed strictly: only the body's
first line counts, and it must match exactly, with `` retired`` before ``-->`` on a
retired issue. A first line that starts ``<!-- bead-mirror`` and names a bead but
does not match, or names another store, makes that issue a *foreign* candidate for
the bead: creation for the bead is held. So does a ``<!-- bead-mirror ... bead=<id>``
marker on any later line of a body whose first line is no banner (a collaborator
added a line above it). Banners count only on issues authored by the mirror account;
an issue whose banner was deleted outright is not recognised.

The body. The banner, a blank line, the description, then ``## Acceptance`` and the
acceptance criteria. ``@name`` and ``#N`` (also ``owner/repo#N``) outside existing
code are wrapped in code spans, in the title too; inside an HTML block, where Markdown
makes no code spans, in ``<code>`` tags. At most 60,000 characters: when the text is
longer it is cut so the banner and a truncation note naming the bead fit.

Eligibility to be created: type in the switch's ``scope``, status ``open``,
``in_progress``, ``review`` or ``blocked``, no ``mirror=never`` metadata and no
``external_ref``; the ``pr`` path (``outbound --bead``) also allows a type outside the
scope when the switch's ``pr_enrol`` is true. Title and body must pass the
private-material screen, or the create is held and reported. ``--no-create`` (the
background run) never creates.

The state (``state.json`` beside the switch, replaced atomically)::

    {"version": 1,
     "binding":  {"store_project_id", "repo_node_id", "account"},
     "enrolled": {bead: {"number", "node_id", "url"}},   # created or adopted
     "pending":  {bead: {"since": ISO time}},             # a create sent, outcome unknown
     "holds":    {bead: {"kind", "reason", "since"}},      # kind: screen, candidates,
                                                          #   pending, link-conflict,
                                                          #   refused (retried each run)
     "tracking": {bead: issue number},                     # linked, not the mirror's
     "retired":  {bead: issue number},                     # retired for the bead
     "ignored":  {bead: [issue numbers]},                  # set aside by `resolve`
     "rebuild":  true}                # until a full run completes a rebuilt state's listing

Create, never twice. Before any create the run lists every issue the mirror account
created in the repository (GraphQL, by the repository's node ID, open and closed,
filtered by creator) and reads the banners; an incomplete listing stops the run.
One live candidate naming this store and bead is adopted; several, or a foreign
one, hold creation; a retired one makes the bead tracking-only. With none, the run
records a pending attempt durably, sends ``createIssue``, and records the number as
soon as it returns. Only an error GitHub reports before executing (a parse or
validation error code such as ``GRAPHQL_VALIDATION_FAILED``, ``UNPROCESSABLE``,
``NOT_FOUND``, ``FORBIDDEN``, with no ``data`` and no error ``path``; auth, rate limit,
unreachable) clears the attempt; any other error (a pathless ``INTERNAL_SERVER_ERROR``
too), partial data, a timeout or a lost reply keeps it pending. A create
GitHub rejects for this bead's input holds that bead (``refused``) and the run goes on.
A pending bead is never sent again: later runs adopt the issue once the listing shows
it, and after a day with no match the bead is held for ``resolve``. ``resolve
--create`` releases only a pending or held create, and refuses while the listing shows
one live issue for the bead (adopt it instead). With no state file the listing runs
even when no bead is eligible for a create, and every run repeats it until one full run
completes it, so an issue whose bead closed before it was linked is still adopted. The link is then
written to the bead's ``external_ref`` only if that field is empty (the same URL is
success; another value is a conflict, reported and left as it is). A link missing from
an enrolled bead is filled only after the issue is read by node ID in the switch's
repository, with its current URL. A link to this repository that is not an issue (a
pull request, or no such number) is not tracked: the bead is held (``bad-link``).

Link checks. Beads that name the same issue (by ``external_ref``, or as enrolled or
tracked in the state; a tracking entry only while the bead has no other link) are
reported on every run and all left alone: no link, adoption, tracking or create for
any of them. ``link``, ``resolve --adopt``, ``overwrite`` and ``retire`` refuse an issue
another bead already names, and a run holds creation rather than adopt one.

Updates. Each full outbound run touches the enrolled beads Beads changed since the
outbound checkpoint, the mirror's issues GitHub reports updated since it (the
``MirrorUpdated`` listing, filtered by creator and ``since``), beads never synced,
beads held open-or-closed and closed beads whose closing comment is not yet recorded.
The checkpoint is the previous full run's start, recorded only when the run finished,
and read back ``CHECKPOINT_MARGIN`` earlier; ``--bead`` runs never move it. (Inbound,
M2.2, will share it.) A touched issue is read fresh by node ID, then each component
converges on the bead: title (compared trimmed), body (line endings normalised,
trailing whitespace removed), and the ``bead-type:`` label (compared without case;
the missing one added and every other ``bead-type:`` label removed, one call each;
no other label is ever touched). Title and body are written in one ``updateIssue``.
A title or body the screen holds is not written and is reported. After the writes
the issue is read back: a component that still differs canonically from what was
sent is marked *not storable* for that desired value (a hash) and is not written
again until the bead's value changes; the create reply counts as the first read-back.
A failed read-back stops the run with nothing confirmed; the next run reads again.

Open or closed follows the spec's hold table against ``confirmed``, the last value a
read-back (or the create reply) showed equal to what was sent: equal to desired, it
is confirmed and any hold clears; observed = confirmed != desired, desired is
written and confirmed only if the read-back equals it (otherwise ``confirmed`` is
unknown and the bead is held); any other difference holds with no write. An
open-or-closed hold persists, reported every run, until GitHub agrees with the bead
or ``overwrite`` writes it. A write whose read-back failed leaves ``confirmed`` as it
was and records the value sent (``sent_state``, saved just before the open-or-closed
write and dropped again if that write is proven not sent): the next run
confirms it if GitHub shows that value, and otherwise holds.

The closing comment. Once the issue is confirmed closed for a closed bead, and this
run's read shows it closed, the run reads every comment (all pages; an incomplete read,
including a page that does not say whether another follows, posts nothing and retries
next run) and posts ``<key>\\nClosed in Beads: <reason>`` unless a comment authored by
the mirror account already carries the key on a line of its own. The key is recorded
only once a fresh read shows the posted comment. The key is
``<!-- bead-mirror close bead=<id> at=<closed_at> reason=<sha256(reason)[:16]> -->``.
The reason is screened (a failing one is posted as "Closed in Beads.") and its
mentions neutralised. Two closes Beads records with the same time and the same
reason have the same key, so the second posts nothing: the key is what the spec
names, and the comment already on the issue states exactly that reason and time.

Retire. ``retire <bead>``, or ``mirror=never`` on an enrolled bead, rewrites only the
banner's first line to its ``retired`` form, as the last write to that issue, reads
it back, and makes the bead tracking-only; any failure stops with the bead still
managed. A retired banner found on GitHub makes the bead tracking-only too. An
enrolled bead missing from Beads is reported, never retired. ``overwrite <bead>
[title|body|label|state]`` reads the issue fresh and writes the bead's values for
every (or only the named) component, ignoring holds and not-storable marks; the
closing comment goes with ``state``. ``map`` prints
bead, issue, link and kind from the state and the links, with no GitHub call.

Enrolled records in the state also carry ``confirmed`` (``OPEN``, ``CLOSED`` or
null), ``not_storable`` ({component: hash}), ``screened`` ({component: why}),
``comment_key``, ``sent_state`` and ``synced``; ``checkpoints`` holds ``{"outbound": ISO time}``, and
an open-or-closed hold has kind ``open-closed``.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import calendar
import errno
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

EXIT_OK = 0
EXIT_SWITCH = 3
EXIT_AUTHORITY = 4
EXIT_GITHUB = 5
EXIT_BEADS = 6
EXIT_BUSY = 7
EXIT_NOT_IMPLEMENTED = 8
EXIT_REFUSED = 9

MIRROR_DIRNAME = "bead-mirror"
STATE_VERSION = 1
DEFAULT_SCOPE = ["epic", "feature", "bug"]
DEFAULT_LOCK_WAIT = 60.0
CHILD_TIMEOUT = 120.0
ELIGIBLE_STATUSES = ("open", "in_progress", "review", "blocked")
BODY_LIMIT = 60_000
PENDING_HOLD_SECONDS = 24 * 3600
LISTING_PAGE = 100
LABEL_PREFIX = "bead-type:"
LABEL_COLOR = "ededed"
# An incremental run looks back this far before the previous run's start, so a change
# stamped by a clock slightly behind (Beads', GitHub's) is not missed.
CHECKPOINT_MARGIN = 5 * 60
COMPONENTS = ("title", "body", "label", "state")

# Ambient settings that would redirect gh to another repository or host.
GH_OVERRIDES = ("GH_REPO", "GH_HOST")
# Git's repository selectors: set (by a caller, or by git for a hook), they would point
# discovery and every git or bd child at another clone than the one the command runs in.
GIT_SELECTORS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
    "GIT_IMPLICIT_WORK_TREE",
)

# Mutation name -> (GraphQL input type, the input field that carries the node ID it addresses).
WRITE_MUTATIONS: dict[str, tuple[str, str]] = {
    "createIssue": ("CreateIssueInput", "repositoryId"),
    "updateIssue": ("UpdateIssueInput", "id"),
    "closeIssue": ("CloseIssueInput", "issueId"),
    "reopenIssue": ("ReopenIssueInput", "issueId"),
    "addComment": ("AddCommentInput", "subjectId"),
    "addLabelsToLabelable": ("AddLabelsToLabelableInput", "labelableId"),
    "removeLabelsFromLabelable": ("RemoveLabelsFromLabelableInput", "labelableId"),
    "createLabel": ("CreateLabelInput", "repositoryId"),
}

LATER_STAGES = (
    "inbound",
    "both",
    "full",
    "dismiss",
    "install-check",
    "supervise",
    "worker",
)


class Stop(Exception):
    """A run must stop: ``code`` is the exit status, the message is the report."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class Unavailable(Stop):
    """GitHub cannot be used now (gh missing, unauthenticated, rate-limited, offline):
    nothing reached it, and nothing later in the run can either."""

    def __init__(self, message: str) -> None:
        super().__init__(EXIT_GITHUB, message)


class WriteUnknown(Stop):
    """A write whose outcome is unknown: GitHub may or may not have applied it."""

    def __init__(self, message: str) -> None:
        super().__init__(EXIT_GITHUB, message)


class RetireFailed(Stop):
    """Retiring one bead's issue failed for a cause of that issue; it stays managed."""

    def __init__(self, message: str) -> None:
        super().__init__(EXIT_GITHUB, message)


class Refused(Stop):
    """GitHub rejected this one request (its input), before writing anything."""

    def __init__(self, message: str) -> None:
        super().__init__(EXIT_GITHUB, message)


# GraphQL error types GitHub reports before executing a mutation. A pathless error
# whose ``extensions.code`` (or ``type``) names a parse or static validation failure was
# also reported before execution. Any other error ("Something went wrong", a pathless
# ``INTERNAL_SERVER_ERROR``, an unknown code) may follow a write that took effect, and so
# may any error with a ``path`` (a field failed while the mutation ran) or a reply with
# ``data`` (partial results): those are never taken as proof nothing was written.
REQUEST_ERROR_TYPES = ("UNPROCESSABLE", "ARGUMENT_ERROR")
ACCOUNT_ERROR_TYPES = ("NOT_FOUND", "FORBIDDEN", "INSUFFICIENT_SCOPES", "RATE_LIMITED")
PRE_EXECUTION_CODES = (
    "GRAPHQL_PARSE_FAILED",
    "GRAPHQL_VALIDATION_FAILED",
    "undefinedField",
    "undefinedType",
    "argumentLiteralsIncompatible",
    "argumentNotAccepted",
    "missingRequiredArguments",
    "missingRequiredInputObjectAttribute",
    "variableMismatch",
    "variableNotDefined",
    "variableNotUsed",
    "selectionMismatch",
)


def error_codes(err: Mapping[str, Any]) -> set[str]:
    """The ``type`` and ``extensions.code`` one GraphQL error carries."""
    ext = err.get("extensions")
    found = {err.get("type"), ext.get("code") if isinstance(ext, dict) else None}
    return {str(c) for c in found if isinstance(c, str) and c}


def reports_rate_limit(body: Any) -> bool:
    """True when any error in a GraphQL reply is GitHub's rate limit, with or without
    partial data. Enough for a read; a write needs ``rate_limited``'s proof."""
    errors = body.get("errors") if isinstance(body, dict) else None
    return isinstance(errors, list) and any(
        isinstance(e, dict) and "RATE_LIMITED" in error_codes(e) for e in errors
    )


def rate_limited(body: Any) -> bool:
    """True when a GraphQL reply reports GitHub's rate limit before executing anything,
    whatever gh's exit status."""
    errors = body.get("errors") if isinstance(body, dict) else None
    return (
        isinstance(errors, list)
        and any(
            isinstance(e, dict) and "RATE_LIMITED" in error_codes(e) for e in errors
        )
        and classify_errors(errors, body.get("data")) is not None
    )


def classify_errors(errors: Any, data: Any = None) -> str | None:
    """ "request" or "account" when a GraphQL reply's ``errors`` (with its ``data``)
    prove nothing was written, else None."""
    if not isinstance(errors, list) or not errors or data is not None:
        return None
    kinds = set()
    for err in errors:
        if not isinstance(err, dict) or err.get("path"):
            return None
        codes = error_codes(err)
        if codes & set(REQUEST_ERROR_TYPES + PRE_EXECUTION_CODES):
            kinds.add("request")
        elif codes & set(ACCOUNT_ERROR_TYPES):
            kinds.add("account")
        else:
            return None
    return "account" if "account" in kinds else "request"


# ---------------------------------------------------------------------------
# Child processes


def child_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """The environment for git, bd and gh: Beads store overrides, Git's repository
    selectors and gh redirects removed."""
    source = os.environ if base is None else base
    env = {
        k: v
        for k, v in source.items()
        if not k.startswith("BEADS_") and k not in GH_OVERRIDES + GIT_SELECTORS
    }
    env["GH_PROMPT_DISABLED"] = "1"
    env["GH_NO_UPDATE_NOTIFIER"] = "1"
    env["NO_COLOR"] = "1"
    return env


def run_child(
    argv: Sequence[str],
    cwd: str | None,
    env: Mapping[str, str],
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    feed: dict[str, Any] = (
        {"stdin": subprocess.DEVNULL} if stdin_text is None else {"input": stdin_text}
    )
    return subprocess.run(
        list(argv),
        cwd=cwd,
        env=dict(env),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
        **feed,
    )


def git_common_dir() -> str | None:
    """The absolute git common directory of the clone the command runs in (its current
    directory, whatever Git's selectors say), or None outside one."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            env=child_env(),
            capture_output=True,
            text=True,
            timeout=CHILD_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # Relative to the current directory when it is one; ``--path-format`` (git 2.31)
    # is not used, since older git echoes an unknown option instead of rejecting it.
    path = proc.stdout.strip()
    if proc.returncode != 0 or not path or "\n" in path:
        return None
    path = os.path.realpath(path)
    return path if os.path.isdir(path) else None


def git_toplevel() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        env=child_env(),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    top = proc.stdout.strip()
    if proc.returncode != 0 or not top:
        raise Stop(
            EXIT_BEADS,
            "cannot find the clone's top level (git rev-parse --show-toplevel)",
        )
    return top


# ---------------------------------------------------------------------------
# The switch


def load_switch(mirror_dir: str) -> dict[str, Any] | None:
    """The validated switch, or None when there is no switch (the silent case)."""
    path = os.path.join(mirror_dir, "switch.json")
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise Stop(EXIT_SWITCH, f"cannot read the switch: {exc.strerror}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise Stop(EXIT_SWITCH, f"the switch is not valid JSON: {exc}") from exc
    return validate_switch(data)


def validate_switch(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise Stop(EXIT_SWITCH, "the switch must be a JSON object")
    problems: list[str] = []
    for key in ("host", "repo", "repo_node_id", "account", "store_project_id"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{key} must be a non-empty string")
    repo = data.get("repo")
    if isinstance(repo, str) and not re.fullmatch(
        r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repo
    ):
        problems.append("repo must be owner/name")
    host = data.get("host")
    if isinstance(host, str) and not re.fullmatch(r"[A-Za-z0-9.-]+(:[0-9]+)?", host):
        problems.append("host must be a bare hostname")
    scope = data.get("scope", DEFAULT_SCOPE)
    if not isinstance(scope, list) or not all(isinstance(t, str) and t for t in scope):
        problems.append("scope must be a list of bead types")
    pr_enrol = data.get("pr_enrol", True)
    if not isinstance(pr_enrol, bool):
        problems.append("pr_enrol must be true or false")
    if problems:
        raise Stop(EXIT_SWITCH, "the switch is invalid: " + "; ".join(problems))
    switch = dict(data)
    switch["scope"] = list(scope)
    switch["pr_enrol"] = pr_enrol
    return switch


# ---------------------------------------------------------------------------
# Beads


def check_store(
    switch: Mapping[str, Any], toplevel: str, env: Mapping[str, str]
) -> str:
    """Resolve the store at the clone's top level and check its identity; return project_id."""
    if shutil.which("bd", path=env.get("PATH")) is None:
        raise Stop(EXIT_BEADS, "bd not found on PATH")
    try:
        proc = run_child(["bd", "context", "--json"], toplevel, env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Stop(EXIT_BEADS, f"bd failed: {exc}") from exc
    try:
        info = json.loads(proc.stdout) if proc.returncode == 0 else None
    except ValueError:
        info = None
    if not isinstance(info, dict) or not isinstance(info.get("project_id"), str):
        first = (proc.stderr.strip().splitlines() or ["no project_id reported"])[0]
        raise Stop(
            EXIT_BEADS,
            "cannot resolve the Beads store at the clone's top level: " + first,
        )
    found = info["project_id"]
    if found != switch["store_project_id"]:
        raise Stop(
            EXIT_AUTHORITY,
            f"the Beads store is a different store: project_id {found}, "
            f"the switch records {switch['store_project_id']}",
        )
    return str(found)


# ---------------------------------------------------------------------------
# GitHub


def looks_like_node_id(value: Any) -> bool:
    """True for a GitHub global node ID (``R_kgDO...`` or legacy base64), never a name or URL."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_+/=-]{4,}", value):
        return False
    if re.fullmatch(r"[A-Z][A-Za-z]{0,3}_[A-Za-z0-9_-]+", value):
        return True
    try:
        decoded = base64.b64decode(value, validate=True).decode("ascii")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return False
    return re.fullmatch(r"\d+:[A-Za-z]+\d+", decoded) is not None


class Gh:
    """Every gh call: ``gh api --hostname <host> ...`` with ambient redirects removed."""

    def __init__(self, host: str, env: Mapping[str, str]) -> None:
        self.host = host
        self.env = dict(env)

    def _run(
        self, args: Sequence[str], stdin_text: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Run gh; a timeout raises ``subprocess.TimeoutExpired`` for the caller to judge."""
        if shutil.which("gh", path=self.env.get("PATH")) is None:
            raise Unavailable("gh not found on PATH")
        argv = ["gh", "api", "--hostname", self.host] + list(args)
        try:
            return run_child(argv, None, self.env, stdin_text)
        except OSError as exc:
            raise Unavailable(f"gh could not run: {exc}") from exc

    def _call(self, args: Sequence[str], stdin_text: str | None = None) -> Any:
        try:
            proc = self._run(args, stdin_text)
        except subprocess.TimeoutExpired as exc:
            raise Unavailable(f"gh timed out reaching {self.host} (offline?)") from exc
        if proc.returncode != 0:
            try:
                failed = json.loads(proc.stdout)
            except ValueError:
                failed = None
            if reports_rate_limit(failed):  # only reads come through here
                raise Unavailable(self.rate_limit_cause())
            cause, kind = self._cause(proc)
            raise (
                Unavailable(cause)
                if kind == "unavailable"
                else Stop(EXIT_GITHUB, cause)
            )
        try:
            return json.loads(proc.stdout)
        except ValueError as exc:
            raise Stop(EXIT_GITHUB, "gh returned something that is not JSON") from exc

    def _cause(self, proc: subprocess.CompletedProcess[str]) -> tuple[str, str | None]:
        """The cause of a failed call, and what it proves: "unavailable" (GitHub cannot
        be used now; nothing reached it), "refused" (GitHub rejected this request before
        executing it) or None (it may have executed)."""
        err = proc.stderr.strip()
        low = err.lower()
        if proc.returncode == 4 or "gh auth login" in low or "(http 401)" in low:
            return (
                f"gh is not authenticated for {self.host} (run gh auth login)",
                "unavailable",
            )
        try:
            body = json.loads(proc.stdout)
        except ValueError:
            body = None
        if (
            "(http 429)" in low
            or ("rate limit" in low and "(http 403)" in low)
            or rate_limited(body)
        ):
            return self.rate_limit_cause(), "unavailable"
        if "error connecting to" in low or "no such host" in low:
            return f"cannot reach {self.host} (offline?)", "unavailable"
        refused = (
            isinstance(body, dict)
            and classify_errors(body.get("errors"), body.get("data")) is not None
        )
        first = (err.splitlines() or [f"exit {proc.returncode}"])[0]
        return "gh failed: " + first, "refused" if refused else None

    def rate_limit_cause(self) -> str:
        return f"GitHub rate limit reached on {self.host}; try again after it resets"

    def rest_get(self, path: str) -> Any:
        return self._call([path])

    def graphql(self, query: str, variables: Mapping[str, Any]) -> dict[str, Any]:
        """One GraphQL read; its ``data``, or Stop."""
        body = json.dumps({"query": query, "variables": dict(variables)})
        result = self._call(["graphql", "--input", "-"], stdin_text=body)
        if reports_rate_limit(result):
            raise Unavailable(self.rate_limit_cause())
        if not isinstance(result, dict) or result.get("errors"):
            errors = result.get("errors") if isinstance(result, dict) else None
            raise Stop(EXIT_GITHUB, f"GitHub refused a read: {json.dumps(errors)}")
        data = result.get("data")
        if not isinstance(data, dict):
            raise Stop(EXIT_GITHUB, "GitHub returned no data")
        return data

    def login(self) -> str:
        data = self.rest_get("user")
        login = data.get("login") if isinstance(data, dict) else None
        if not isinstance(login, str):
            raise Stop(EXIT_GITHUB, "gh did not report a login")
        return login

    def graphql_write(
        self,
        mutation: str,
        subject_id: str,
        fields: Mapping[str, Any],
        selection: str,
    ) -> Any:
        """Run one write mutation addressed by ``subject_id``, which must be a node ID.

        Raises ``Refused`` when GitHub rejected this request's input, ``Stop`` when it
        definitely did not apply the write for a cause beyond this request (account,
        rate limit, offline), and ``WriteUnknown`` when it may have applied it.
        """
        if mutation not in WRITE_MUTATIONS:
            raise ValueError(f"not a mirror write mutation: {mutation}")
        input_type, id_field = WRITE_MUTATIONS[mutation]
        if not looks_like_node_id(subject_id):
            raise ValueError(f"writes are addressed by node ID, not {subject_id!r}")
        if id_field in fields:
            raise ValueError("pass the addressed node ID as subject_id, not in fields")
        payload = dict(fields)
        payload[id_field] = subject_id
        query = f"mutation($input: {input_type}!) {{ {mutation}(input: $input) {{ {selection} }} }}"
        body = json.dumps({"query": query, "variables": {"input": payload}})
        try:
            proc = self._run(["graphql", "--input", "-"], stdin_text=body)
        except subprocess.TimeoutExpired as exc:
            raise WriteUnknown(
                f"{mutation}: gh timed out; the outcome is unknown"
            ) from exc
        try:
            result: Any = json.loads(proc.stdout)
        except ValueError:
            result = None
        errors = result.get("errors") if isinstance(result, dict) else None
        data = result.get("data") if isinstance(result, dict) else None
        if proc.returncode == 0 and rate_limited(result):
            raise Unavailable(f"{mutation} was not sent: {self.rate_limit_cause()}")
        if proc.returncode != 0 or errors:
            kind = classify_errors(errors, data)
            cause, proof = (
                self._cause(proc)
                if proc.returncode != 0
                else (json.dumps(errors), "refused" if kind else None)
            )
            if proof is None:
                raise WriteUnknown(f"{mutation}: {cause}; the outcome is unknown")
            if proof == "unavailable":
                raise Unavailable(f"{mutation} was not sent: {cause}")
            if kind == "request":
                raise Refused(f"GitHub refused {mutation}: {cause}")
            raise Stop(EXIT_GITHUB, f"GitHub refused {mutation}: {cause}")
        if not isinstance(result, dict):
            raise WriteUnknown(f"{mutation}: the reply was not JSON")
        if not isinstance(data, dict) or not isinstance(data.get(mutation), dict):
            raise WriteUnknown(f"{mutation}: the reply had no result")
        return data[mutation]


def check_github(switch: Mapping[str, Any], gh: Gh) -> None:
    """The account and repository checks; the only call that names the repository."""
    host, repo_name, account = switch["host"], switch["repo"], switch["account"]
    login = gh.login()
    if login != account:
        raise Stop(
            EXIT_AUTHORITY,
            f"gh is logged in as {login} on {host}; the switch's mirror account is {account}",
        )
    try:
        repo = gh.rest_get(f"repos/{repo_name}")
    except Stop as exc:
        if "(HTTP 404)" in str(exc):
            raise Stop(
                EXIT_AUTHORITY,
                f"repository {repo_name} not found on {host} for {account}",
            ) from exc
        raise
    node_id = repo.get("node_id") if isinstance(repo, dict) else None
    if node_id != switch["repo_node_id"]:
        raise Stop(
            EXIT_AUTHORITY,
            f"repository {repo_name} on {host} has node ID {node_id}; "
            f"the switch records {switch['repo_node_id']}",
        )


# ---------------------------------------------------------------------------
# State and lock


def binding_of(switch: Mapping[str, Any]) -> dict[str, str]:
    return {
        "store_project_id": switch["store_project_id"],
        "repo_node_id": switch["repo_node_id"],
        "account": switch["account"],
    }


def load_state(mirror_dir: str, switch: Mapping[str, Any]) -> dict[str, Any] | None:
    """The state, or None when there is none; Stop when it is bound elsewhere or unreadable."""
    path = os.path.join(mirror_dir, "state.json")
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise Stop(
            EXIT_AUTHORITY, f"the state file is unreadable ({exc}); run reset-state"
        ) from exc
    bound = state.get("binding") if isinstance(state, dict) else None
    if not isinstance(bound, dict):
        raise Stop(EXIT_AUTHORITY, "the state file has no binding; run reset-state")
    want = binding_of(switch)
    labels = {
        "store_project_id": "store",
        "repo_node_id": "repository",
        "account": "mirror account",
    }
    wrong = [
        f"{labels[k]} (state {bound.get(k)}, switch {want[k]})"
        for k in want
        if bound.get(k) != want[k]
    ]
    if wrong:
        raise Stop(
            EXIT_AUTHORITY,
            f"the state file is bound to another {', '.join(wrong)}; "
            "no writes until the owner runs reset-state",
        )
    return dict(state)


def write_json_atomic(path: str, data: Any) -> None:
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=".state-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    fsync_dir(directory)


def fsync_dir(directory: str) -> None:
    dfd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


class CloneLock:
    """The clone-wide lock beside the switch, waited for up to ``wait`` seconds."""

    def __init__(self, mirror_dir: str, wait: float) -> None:
        self.path = os.path.join(mirror_dir, "lock")
        self.wait = wait
        self.fd: int | None = None

    def __enter__(self) -> CloneLock:  # noqa: PYI034
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        deadline = time.monotonic() + max(self.wait, 0.0)
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
                    os.close(fd)
                    raise
            if time.monotonic() >= deadline:
                os.close(fd)
                raise Stop(
                    EXIT_BUSY,
                    f"busy: another mirror run holds the lock (waited {self.wait:g}s)",
                )
            time.sleep(0.05)
        self.fd = fd
        return self

    def __exit__(self, *exc: object) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


# ---------------------------------------------------------------------------
# Text: the banner, the body, mentions and the private-material screen

BANNER_RE = re.compile(
    r"<!-- bead-mirror v1 store=([A-Za-z0-9._:-]+) bead=([A-Za-z0-9._-]+)( retired)? -->"
)
BANNER_START_RE = re.compile(r"<!--\s*bead-mirror\b")
# Loose reads stop before ``-->``, so ``bead=x-->`` still names bead ``x``.
BANNER_BEAD_RE = re.compile(r"\bbead=([A-Za-z0-9._-]+?)(?=-->|[^A-Za-z0-9._-]|$)")
BANNER_STORE_RE = re.compile(r"\bstore=([A-Za-z0-9._:-]+?)(?=-->|[^A-Za-z0-9._:-]|$)")
VISIBLE_SENTENCE = (
    "> Generated from bead `{bead}` in Beads. Its text follows the bead, so please "
    "comment instead of editing: edits to this title or text are replaced."
)
TRUNCATION_NOTE = "\n\n_Truncated: the full text is in bead `{bead}`._"

# Existing code (fenced blocks, inline spans) is left as it is; mentions outside it
# are wrapped in code spans so publishing notifies no one and cross-links nothing.
# Code is found as CommonMark finds it: a fence only on a line of its own (up to three
# spaces of indent), closed by a fence line of the same character at least as long, or
# the end of the text; an inline span is a backtick run closed by a run of the same
# length on the same line (a span across lines is treated as text, which only costs
# its look). Any other backtick is literal and is escaped.
FENCE_OPEN_RE = re.compile(r" {0,3}(`{3,}(?=[^`\n]*$)|~{3,})", re.MULTILINE)
BACKTICK_RUN_RE = re.compile(r"`+")
ESCAPABLE = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
# GitHub mentions ``@name`` after the start or any non-word character. ``_`` and ``*``
# are emphasis delimiters, not part of a name (``_@alice_`` still mentions alice once
# rendered), so a mention is wrapped after anything but a letter or digit: ``@@alice``,
# ``team-@alice`` and ``docs/@alice`` too. A reference (``#N``, ``owner/repo#N``) keeps
# the narrower boundary, so a URL fragment such as ``example.com/page#12`` stays a link.
MENTION_RE = re.compile(
    r"(?:(?<![A-Za-z0-9])@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:/[A-Za-z0-9_.-]+)?"
    r"|(?<![A-Za-z0-9@/.&-])(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+)"
    r"(?![A-Za-z0-9])"
)
# A CommonMark HTML block leaves its text raw (no code spans, no fences), so a mention
# in one is put in ``<code>`` tags instead; tags themselves are left alone. Detection is
# generous (any container prefix, any tag alone on its line, up to a blank line), which
# is safe: ``<code>`` is also code as inline HTML in an ordinary paragraph.
HTML_BLOCK_TAGS = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|"
    "dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|"
    "frameset|h1|h2|h3|h4|h5|h6|head|header|hr|html|iframe|legend|li|link|main|menu|"
    "menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|"
    "tbody|td|tfoot|th|thead|title|tr|track|ul"
)
HTML_PREFIX = r"[ \t]*(?:(?:>|[-*+]|[0-9]{1,9}[.)])[ \t]*)*"
HTML_RAW_START_RE = re.compile(
    HTML_PREFIX + r"<(script|pre|style|textarea)(?=[\s>]|$)", re.IGNORECASE
)
HTML_SPECIAL_STARTS = (
    (re.compile(HTML_PREFIX + r"<!--"), "-->"),
    (re.compile(HTML_PREFIX + r"<\?"), "?>"),
    (re.compile(HTML_PREFIX + r"<!\[CDATA\["), "]]>"),
    (re.compile(HTML_PREFIX + r"<![A-Za-z]"), ">"),
)
HTML_BLOCK_START_RE = re.compile(
    HTML_PREFIX
    + r"(?:</?(?:"
    + HTML_BLOCK_TAGS
    + r")(?=[\s/>]|$)"
    + r"|</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>[ \t]*$)",
    re.IGNORECASE,
)
HTML_TAG_RE = re.compile(r"<[^<>]*>")
# Where a mention in ordinary text is not live, so it is left as written: a URL GFM
# autolinks (start, whitespace, ``*``, ``_``, ``~`` or ``(`` before it, a domain with
# a period and no underscore), a valid inline HTML tag (its attributes are not text)
# and an angle-bracket autolink. Wrapping one would only break the link.
INLINE_SAFE_RE = re.compile(
    r"(?<![^\s*_~(])https?://[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+[^\s<]*"
    r"|<[A-Za-z][A-Za-z0-9-]*"
    r"(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s\"'=<>`]+|'[^']*'|\"[^\"]*\"))?)*"
    r"\s*/?>"
    r"|</[A-Za-z][A-Za-z0-9-]*\s*>"
    r"|<[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*>"
)
TITLE_LIMIT = 256

# Best-effort: what a public issue must not carry. Reported by label, never by match.
PRIVATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "a home or workspace path",
        re.compile(
            r"(?<![\w.])(?:/home/|/Users/)[A-Za-z0-9._-]+(?![A-Za-z0-9._-])"
            r"|(?<![\w.])/root/"
            r"|\b[A-Za-z]:\\Users\\"
            # An absolute path of three or more segments under a common workspace or
            # server root; not inside a URL (a host, port or path segment precedes it).
            r"|(?<![\w.:/~-])/(?:data|srv|mnt|opt|workspaces?|var)"
            r"(?:/[A-Za-z0-9._~+-]+){2,}",
            re.IGNORECASE,
        ),
    ),
    ("a file URL", re.compile(r"\bfile://", re.IGNORECASE)),
    (
        "an internal hostname",
        re.compile(
            r"\blocalhost\b|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*"
            r"\.(?:local|internal|lan|corp|home\.arpa)(?![A-Za-z0-9-]|\.[A-Za-z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "a private IP address",
        re.compile(
            r"(?<![\d.])(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}"
            r"|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|127(?:\.\d{1,3}){3}"
            r"|169\.254(?:\.\d{1,3}){2})(?::\d+)?(?![\d.]*\d)"
        ),
    ),
    (
        "something that looks like a credential",
        re.compile(
            r"\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}"
            r"|\bsk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*-----"
        ),
    ),
)


def banner_line(store: str, bead: str, retired: bool = False) -> str:
    mark = " retired" if retired else ""
    return f"<!-- bead-mirror v1 store={store} bead={bead}{mark} -->"


def read_banner(body: str) -> dict[str, Any] | None:
    """The banner on a body's first line: {store, bead, retired, strict}, or None."""
    first = (body or "").lstrip("﻿").split("\n", 1)[0].rstrip()
    strict = BANNER_RE.fullmatch(first)
    if strict:
        return {
            "store": strict.group(1),
            "bead": strict.group(2),
            "retired": bool(strict.group(3)),
            "strict": True,
        }
    if not BANNER_START_RE.match(first):
        return None
    bead = BANNER_BEAD_RE.search(first)
    if bead is None:
        return None
    store = BANNER_STORE_RE.search(first)
    return {
        "store": store.group(1) if store else None,
        "bead": bead.group(1),
        "retired": "retired" in first,
        "strict": False,
    }


def stray_banner_beads(body: str) -> list[str]:
    """The beads named by banner markers anywhere in ``body`` (read loosely)."""
    beads: list[str] = []
    for start in BANNER_START_RE.finditer(body or ""):
        line = body[start.start() : _end_of_line(body, start.start())]
        bead = BANNER_BEAD_RE.search(line)
        if bead and bead.group(1) not in beads:
            beads.append(bead.group(1))
    return beads


def _wrap_tokens(text: str, prev: str = "") -> list[tuple[str, str]]:
    """Plain text as ("text" | "wrap", piece) tokens, each mention in its own code span.

    ``prev`` is the text just before (its last character decides whether a URL at the
    start is autolinked); nothing before counts as the start of a line.
    """
    tokens: list[tuple[str, str]] = []
    context = prev[-1:] or "\n"
    safe = [
        (s.start() - 1, s.end() - 1) for s in INLINE_SAFE_RE.finditer(context + text, 1)
    ]
    at = 0
    for m in MENTION_RE.finditer(text):
        if any(a <= m.start() < b for a, b in safe):
            continue
        before = text[at : m.start()]
        if (len(before) - len(before.rstrip("\\"))) % 2:
            # A backslash here would escape the span's opening backtick: an escaped
            # "@" or "#" loses its backslash (it renders the same), any other is doubled.
            before = before[:-1] if m.group(0)[0] in "@#" else before + "\\"
        if before:
            tokens.append(("text", before))
        tokens.append(("wrap", f"`{m.group(0)}`"))
        at = m.end()
    if at < len(text):
        tokens.append(("text", text[at:]))
    return tokens


def _fence_end(text: str, at: int, fence: str) -> int:
    """Where the fenced block whose opening fence starts at ``at`` ends."""
    closer = re.compile(
        r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$",
        re.MULTILINE,
    )
    line_end = text.find("\n", at)
    if line_end < 0:
        return len(text)
    m = closer.search(text, line_end + 1)
    return m.end() if m else len(text)


def _inline_parts(text: str) -> list[tuple[str, str]]:
    """Text with no fences as ("text" | "code", piece); literal backticks escaped."""
    parts: list[tuple[str, str]] = []
    plain: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text) and text[i + 1] in ESCAPABLE:
            plain.append(text[i : i + 2])  # an escape the author wrote
            i += 2
            continue
        if ch != "`":
            plain.append(ch)
            i += 1
            continue
        run = BACKTICK_RUN_RE.match(text, i).group(0)  # type: ignore[union-attr]
        line_end = text.find("\n", i)
        line_end = len(text) if line_end < 0 else line_end
        close = next(
            (
                m
                for m in BACKTICK_RUN_RE.finditer(text, i + len(run), line_end)
                if len(m.group(0)) == len(run)
            ),
            None,
        )
        if close is None:
            plain.append("\\`" * len(run))  # no closer: literal backticks
            i += len(run)
            continue
        if plain:
            parts.append(("text", "".join(plain)))
            plain = []
        parts.append(("code", text[i : close.end()]))
        i = close.end()
    if plain:
        parts.append(("text", "".join(plain)))
    return parts


def _end_of_line(text: str, at: int) -> int:
    end = text.find("\n", at)
    return len(text) if end < 0 else end


def _html_block_end(text: str, at: int) -> int | None:
    """Where an HTML block starting on the line at ``at`` ends, or None if none starts."""
    line = text[at : _end_of_line(text, at)]
    raw = HTML_RAW_START_RE.match(line)
    if raw:
        closer = re.compile(r"</(?:script|pre|style|textarea)>", re.IGNORECASE)
        found = closer.search(text, at + raw.end())
        return len(text) if found is None else _end_of_line(text, found.end())
    for start, marker in HTML_SPECIAL_STARTS:
        special = start.match(line)
        if special:
            found_at = text.find(marker, at + special.end())
            if found_at < 0:
                return len(text)
            return _end_of_line(text, found_at + len(marker))
    if HTML_BLOCK_START_RE.match(line):
        blank = re.compile(r"\n[ \t]*(?:\n|$)").search(text, at)
        return len(text) if blank is None else blank.start()
    return None


def code_parts(text: str, blocks: bool = True) -> list[tuple[str, str]]:
    """``text`` as ("text" | "code" | "html", piece): the author's code, HTML blocks
    (only when ``blocks``), and the rest with literal backticks escaped."""
    parts: list[tuple[str, str]] = []
    plain = 0  # where the text not yet classified starts
    at = 0  # the start of the line being looked at
    while at < len(text):
        fence = FENCE_OPEN_RE.match(text, at)
        kind, end = "code", None
        if fence:
            end = _fence_end(text, at, fence.group(1))
        elif blocks:
            kind, end = "html", _html_block_end(text, at)
        if end is None:
            at = _end_of_line(text, at) + 1
            continue
        if at > plain:
            parts += _inline_parts(text[plain:at])
        parts.append((kind, text[at:end]))
        plain = at = end
        if at < len(text):
            at += 1  # the newline after the block is text
    if plain < len(text):
        parts += _inline_parts(text[plain:])
    return parts


def _html_tokens(text: str) -> list[tuple[str, str]]:
    """HTML block text as ("html" | "wrap", piece): each mention outside a tag in
    ``<code>`` tags; tags and the rest left exactly as written."""
    tokens: list[tuple[str, str]] = []
    at = 0
    for tag in list(HTML_TAG_RE.finditer(text)) + [None]:
        stop = len(text) if tag is None else tag.start()
        for m in MENTION_RE.finditer(text, at, stop):
            if m.start() > at:
                tokens.append(("html", text[at : m.start()]))
            tokens.append(("wrap", f"<code>{m.group(0)}</code>"))
            at = m.end()
        if tag is not None:
            tokens.append(("html", text[at : tag.end()]))
            at = tag.end()
    if at < len(text):
        tokens.append(("html", text[at:]))
    return tokens


def neutral_tokens(text: str, blocks: bool = True) -> list[tuple[str, str]]:
    """``text`` as ("text" | "wrap" | "code" | "html", piece) tokens, mentions wrapped.

    "code" is code the author wrote (left as it is), "wrap" a mention the mirror put in
    a code span (``<code>`` tags inside an HTML block), "html" the rest of an HTML block
    as written, "text" the rest with literal backticks escaped. A mention right beside
    the author's code span gets a space between, so their backticks never merge into
    one run. A cut between tokens, or inside a "text" or "html" token, never splits a
    code span. ``blocks=False`` (a title, where GitHub renders no HTML) finds no HTML
    blocks.
    """
    tokens: list[tuple[str, str]] = []
    prev = ""
    for kind, part in code_parts(text, blocks):
        if kind == "code":
            tokens.append(("code", part))
        elif kind == "html":
            tokens += _html_tokens(part)
        else:
            tokens += _wrap_tokens(part, prev)
        prev = part
    spaced: list[tuple[str, str]] = []
    for kind, piece in tokens:
        if (
            spaced
            and {kind, spaced[-1][0]} == {"wrap", "code"}
            and (spaced[-1][1].endswith("`") or piece.startswith("`"))
        ):
            spaced.append(("text", " "))
        spaced.append((kind, piece))
    return spaced


def neutralise(text: str) -> str:
    """Wrap ``@name`` and ``#N`` outside existing code in code spans."""
    return "".join(piece for _, piece in neutral_tokens(text))


def cut_tokens(tokens: Sequence[tuple[str, str]], room: int) -> str:
    """The longest prefix of ``tokens`` within ``room`` characters that splits no span.

    A cut inside text or an HTML block re-wraps a mention the cut exposes, shortened
    until the re-wrapped text fits (never one character over); a cut inside an HTML
    block never ends inside a tag or an open comment; a cut inside a fenced block
    closes the fence; a code span (the author's or the mirror's) is kept whole or left
    out.
    """
    out: list[str] = []
    left = room
    for kind, piece in tokens:
        if len(piece) <= left:
            out.append(piece)
            left -= len(piece)
            continue
        if kind in ("text", "html"):
            out.append(_cut_text(kind, piece, left, out[-1] if out else ""))
        elif kind == "code":
            fence = FENCE_OPEN_RE.match(piece)
            if fence and left > 2 * len(fence.group(1)) + 2:
                run = fence.group(1)
                out.append(piece[: left - len(run) - 1].rstrip("`~") + "\n" + run)
        break
    return "".join(out)


def _cut_text(kind: str, piece: str, room: int, prev: str) -> str:
    """The longest prefix of a "text" or "html" piece that, re-wrapped, fits ``room``."""
    cut = piece[:room]
    while cut:
        if kind == "text" and cut.endswith("\\") and not cut.endswith("\\\\"):
            cut = cut[:-1]  # never split an escape
        elif kind == "html":
            if cut.rfind("<") > cut.rfind(">"):
                cut = cut[: cut.rfind("<")]  # never end inside a tag
            if cut.rfind("<!--") > cut.rfind("-->"):
                cut = cut[: cut.rfind("<!--")]  # nor inside a comment
        tokens = _wrap_tokens(cut, prev) if kind == "text" else _html_tokens(cut)
        done = "".join(p for _, p in tokens)
        if len(done) <= room:
            return done
        cut = cut[:-1]
    return ""


def screen(text: str) -> str | None:
    """The kind of private material ``text`` seems to hold, or None."""
    for label, pattern in PRIVATE_PATTERNS:
        if pattern.search(text):
            return label
    return None


def clean(text: Any) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def issue_title(bead: Mapping[str, Any]) -> str:
    """The neutralised title, bounded to GitHub's title limit with an ellipsis."""
    tokens = neutral_tokens(clean(bead.get("title")), blocks=False)
    title = "".join(piece for _, piece in tokens)
    if len(title) <= TITLE_LIMIT:
        return title
    return cut_tokens(tokens, TITLE_LIMIT - 1).rstrip() + "…"


def issue_body(store: str, bead: Mapping[str, Any]) -> str:
    bead_id = str(bead["id"])
    head = banner_line(store, bead_id) + "\n" + VISIBLE_SENTENCE.format(bead=bead_id)
    tokens: list[tuple[str, str]] = []
    description = clean(bead.get("description"))
    acceptance = clean(bead.get("acceptance_criteria"))
    if description:
        tokens += neutral_tokens(description)
    if acceptance:
        tokens.append(("text", ("\n\n" if tokens else "") + "## Acceptance\n\n"))
        tokens += neutral_tokens(acceptance)
    text = "".join(piece for _, piece in tokens)
    body = head + ("\n\n" + text if text else "")
    if len(body) <= BODY_LIMIT:
        return body
    note = TRUNCATION_NOTE.format(bead=bead_id)
    room = BODY_LIMIT - len(head) - 2 - len(note)
    return head + "\n\n" + cut_tokens(tokens, room).rstrip() + note


def screen_bead(bead: Mapping[str, Any]) -> str | None:
    """Why the bead's title or body is held by the screen, or None."""
    title = screen(clean(bead.get("title")))
    if title:
        return f"the title holds {title}"
    for field in ("description", "acceptance_criteria"):
        found = screen(clean(bead.get(field)))
        if found:
            return f"the body holds {found}"
    return None


# ---------------------------------------------------------------------------
# Beads reads and the one Beads write


def read_beads(toplevel: str, env: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    """Every bead in the store, from ``bd export`` (never ``bd show``)."""
    try:
        proc = run_child(["bd", "export"], toplevel, env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Stop(EXIT_BEADS, f"bd export failed: {exc}") from exc
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or [f"exit {proc.returncode}"])[0]
        raise Stop(EXIT_BEADS, f"bd export failed: {first}")
    beads: dict[str, dict[str, Any]] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise Stop(EXIT_BEADS, "bd export printed a line that is not JSON") from exc
        if (
            isinstance(row, dict)
            and row.get("_type", "issue") == "issue"
            and row.get("id")
        ):
            beads[str(row["id"])] = row
    return beads


def issue_number_in(ref: str, switch: Mapping[str, Any]) -> int | None:
    """The issue number when ``ref`` is an issue URL in the switch's repository."""
    m = re.fullmatch(
        r"https://([^/\s]+)/([^/\s]+)/([^/\s]+)/issues/([0-9]+)/?", ref.strip()
    )
    if m is None or m.group(1).lower() != str(switch["host"]).lower():
        return None
    if f"{m.group(2)}/{m.group(3)}".lower() != str(switch["repo"]).lower():
        return None
    return int(m.group(4))


def write_link(
    ctx: Context, bead_id: str, url: str, number: int, actor: str
) -> tuple[str, str]:
    """Write ``url`` to the bead's ``external_ref`` if it is empty, under the lock.

    Returns ("written" | "same" | "conflict", the value found).
    """
    bead = read_beads(ctx.toplevel, ctx.env).get(bead_id)
    if bead is None:
        raise Stop(EXIT_BEADS, f"bead {bead_id} is no longer in the store")
    found = str(bead.get("external_ref") or "").strip()
    if found:
        same = found == url or issue_number_in(found, ctx.switch) == number
        return ("same" if same else "conflict"), found
    argv = ["bd", "update", bead_id, "--external-ref", url, "--actor", actor]
    try:
        proc = run_child(argv, ctx.toplevel, ctx.env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Stop(EXIT_BEADS, f"bd update failed: {exc}") from exc
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or [f"exit {proc.returncode}"])[0]
        raise Stop(EXIT_BEADS, f"recording the link on {bead_id} failed: {first}")
    return "written", url


# ---------------------------------------------------------------------------
# GitHub reads

ISSUE_FIELDS = "__typename id number url state author { login } body"
LIST_QUERY = (
    "query MirrorIssues($id: ID!, $creator: String!, $first: Int!, $after: String) {"
    " node(id: $id) { ... on Repository {"
    " issues(first: $first, after: $after, filterBy: {createdBy: $creator},"
    " states: [OPEN, CLOSED], orderBy: {field: CREATED_AT, direction: ASC}) {"
    f" nodes {{ {ISSUE_FIELDS} }} pageInfo {{ hasNextPage endCursor }} }} }} }} }}"
)
LABEL_QUERY = (
    "query MirrorLabel($id: ID!, $name: String!) {"
    " node(id: $id) { ... on Repository { label(name: $name) { id name } } } }"
)
ISSUE_QUERY = (
    "query MirrorIssue($id: ID!, $number: Int!) {"
    " node(id: $id) { ... on Repository { issueOrPullRequest(number: $number) {"
    f" ... on Issue {{ {ISSUE_FIELDS} }} ... on PullRequest {{ __typename id number url }}"
    " } } } }"
)
CREATE_SELECTION = f"issue {{ {ISSUE_FIELDS} title }}"


def as_issue(node: Any) -> dict[str, Any] | None:
    """The fields the mirror keeps for an issue node, or None when it is malformed."""
    if not isinstance(node, dict):
        return None
    number, node_id, url = node.get("number"), node.get("id"), node.get("url")
    if not isinstance(number, int) or not isinstance(url, str):
        return None
    if not looks_like_node_id(node_id):
        return None
    author: dict[str, Any] = (
        node["author"] if isinstance(node.get("author"), dict) else {}
    )
    return {
        "number": number,
        "node_id": node_id,
        "url": url,
        "state": node.get("state"),
        "author": author.get("login"),
        "body": node.get("body") or "",
    }


def list_mirror_issues(ctx: Context) -> list[dict[str, Any]]:
    """Every issue the mirror account created, open and closed; Stop if incomplete."""
    issues: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        variables = {
            "id": ctx.switch["repo_node_id"],
            "creator": ctx.switch["account"],
            "first": LISTING_PAGE,
            "after": after,
        }
        try:
            data = ctx.gh.graphql(LIST_QUERY, variables)
        except Stop as exc:
            raise Stop(
                EXIT_GITHUB,
                f"the issues listing is incomplete ({exc}); nothing was created",
            ) from exc
        conn = (data.get("node") or {}).get("issues")
        nodes = conn.get("nodes") if isinstance(conn, dict) else None
        if not isinstance(nodes, list):
            raise Stop(
                EXIT_GITHUB, "the issues listing is incomplete; nothing was created"
            )
        for node in nodes:
            issue = as_issue(node)
            if issue is not None:
                issues.append(issue)
        more, after = next_page(conn, after)
        if not more:
            return issues
        if after is None:
            raise Stop(
                EXIT_GITHUB, "the issues listing is incomplete; nothing was created"
            )


def next_page(conn: Any, after: str | None) -> tuple[bool, str | None]:
    """(another page follows, its cursor) from a connection's ``pageInfo``. Only an
    explicit ``hasNextPage: false`` ends a listing; with another page, a cursor that is
    missing or does not move on is returned as None, and the listing is incomplete."""
    page = conn.get("pageInfo") if isinstance(conn, dict) else None
    more = page.get("hasNextPage") if isinstance(page, dict) else None
    if more is False:
        return False, None
    cursor = page.get("endCursor") if isinstance(page, dict) else None
    if more is not True or not isinstance(cursor, str) or not cursor or cursor == after:
        return True, None
    return True, cursor


def candidates_by_bead(
    issues: Sequence[Mapping[str, Any]], account: str, store: str
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Mirror-authored issues by the bead their banner names: live, foreign, retired."""
    found: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for issue in issues:
        if issue.get("author") != account:
            continue  # an issue not authored by the mirror account is never adopted
        body = str(issue.get("body") or "")
        banner = read_banner(body)
        if banner is None:
            # Edited off line 1 (a line added above it): never adopted, but it holds.
            for bead in stray_banner_beads(body):
                slot = found.setdefault(
                    bead, {"live": [], "foreign": [], "retired": []}
                )
                slot["foreign"].append(dict(issue))
            continue
        slot = found.setdefault(
            banner["bead"], {"live": [], "foreign": [], "retired": []}
        )
        if not banner["strict"] or banner["store"] != store:
            slot["foreign"].append(dict(issue))
        elif banner["retired"]:
            slot["retired"].append(dict(issue))
        else:
            slot["live"].append(dict(issue))
    return found


def issues_named(
    beads: Mapping[str, Mapping[str, Any]],
    state: Mapping[str, Any] | None,
    switch: Mapping[str, Any],
) -> dict[int, set[str]]:
    """Issue number -> the beads that name it: by ``external_ref`` or in the state.

    A tracking entry counts only while the bead's link names that issue: once Beads
    links the bead elsewhere or clears its link, the entry is stale and claims nothing.
    Retirement evidence (``retired``) follows the same rule: it claims the issue only
    while the bead's link names it; the retired banner on GitHub already prevents a
    second create or an adoption."""
    named: dict[int, set[str]] = {}
    for bead_id, bead in beads.items():
        number = issue_number_in(str(bead.get("external_ref") or ""), switch)
        if number is not None:
            named.setdefault(number, set()).add(bead_id)
    for bead_id, record in ((state or {}).get("enrolled") or {}).items():
        if isinstance(record, dict) and isinstance(record.get("number"), int):
            named.setdefault(record["number"], set()).add(bead_id)
    for key in ("tracking", "retired"):
        for bead_id, number in ((state or {}).get(key) or {}).items():
            ref = str((beads.get(bead_id) or {}).get("external_ref") or "").strip()
            if isinstance(number, int) and issue_number_in(ref, switch) == number:
                named.setdefault(number, set()).add(bead_id)
    return named


def fetch_issue(ctx: Context, number: int) -> dict[str, Any] | None:
    """Issue or pull request ``number`` in the switch's repository, or None if missing."""
    try:
        data = ctx.gh.graphql(
            ISSUE_QUERY, {"id": ctx.switch["repo_node_id"], "number": number}
        )
    except Stop as exc:
        if "could not resolve to an issue or pull request" in str(exc).lower():
            return None
        raise
    node = (data.get("node") or {}).get("issueOrPullRequest")
    return node if isinstance(node, dict) else None


def checked_issue(ctx: Context, number: int) -> tuple[dict[str, Any] | None, str]:
    """Issue ``number`` in the switch's repository (looked up by the repository's node
    ID), or None and why it is not one."""
    node = fetch_issue(ctx, number)
    if node is None:
        return None, f"#{number} does not exist in {ctx.switch['repo']}"
    issue = as_issue(node) if node.get("__typename") == "Issue" else None
    if issue is None:
        return None, f"#{number} is a pull request, not an issue"
    return issue, ""


NODE_FIELDS = (
    "__typename id number url state title body updatedAt author { login }"
    " repository { id } labels(first: 100) { nodes { id name } }"
)
NODE_QUERY = (
    "query MirrorIssueNode($id: ID!) {"
    f" node(id: $id) {{ ... on Issue {{ {NODE_FIELDS} }} }} }}"
)
UPDATED_QUERY = (
    "query MirrorUpdated($id: ID!, $creator: String!, $since: DateTime!,"
    " $first: Int!, $after: String) {"
    " node(id: $id) { ... on Repository {"
    " issues(first: $first, after: $after,"
    " filterBy: {createdBy: $creator, since: $since}, states: [OPEN, CLOSED]) {"
    " nodes { id number } pageInfo { hasNextPage endCursor } } } } }"
)
COMMENTS_QUERY = (
    "query MirrorComments($id: ID!, $first: Int!, $after: String) {"
    " node(id: $id) { ... on Issue { comments(first: $first, after: $after) {"
    " nodes { author { login } body } pageInfo { hasNextPage endCursor } } } } }"
)
WRITE_SELECTION = "issue { id }"
LABEL_SELECTION = "clientMutationId"


def read_node(ctx: Context, node_id: str) -> dict[str, Any] | None:
    """An issue read fresh by its node ID, with title and labels; None if it is gone
    or no longer in the switch's repository (a transfer keeps the node ID)."""
    try:
        data = ctx.gh.graphql(NODE_QUERY, {"id": node_id})
    except Stop as exc:
        if "could not resolve to a node with the global id" in str(exc).lower():
            return None
        raise
    node = data.get("node")
    if not isinstance(node, dict) or node.get("__typename") != "Issue":
        return None
    if (node.get("repository") or {}).get("id") != ctx.switch["repo_node_id"]:
        return None
    issue = as_issue(node)
    if issue is None:
        return None
    labels = (node.get("labels") or {}).get("nodes") or []
    issue["title"] = str(node.get("title") or "")
    issue["labels"] = [
        (str(lb["id"]), str(lb["name"]))
        for lb in labels
        if isinstance(lb, dict) and isinstance(lb.get("name"), str) and lb.get("id")
    ]
    return issue


def paged(
    ctx: Context, query: str, variables: Mapping[str, Any], path: Sequence[str]
) -> list[Any] | None:
    """Every node of a paginated connection at ``path`` under ``data``; None if incomplete."""
    nodes: list[Any] = []
    after: str | None = None
    while True:
        try:
            data: Any = ctx.gh.graphql(
                query, dict(variables, first=LISTING_PAGE, after=after)
            )
        except Unavailable:
            raise  # its cause ends the run; a manual run exits non-zero with it
        except Stop:
            return None
        for key in path:
            data = data.get(key) if isinstance(data, dict) else None
        page_nodes = data.get("nodes") if isinstance(data, dict) else None
        if not isinstance(page_nodes, list):
            return None
        nodes += page_nodes
        more, after = next_page(data, after)
        if not more:
            return nodes
        if after is None:
            return None


def canon_title(text: Any) -> str:
    return str(text or "").strip()


def canon_body(text: Any) -> str:
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip()


def canon_label(name: Any) -> str:
    return str(name or "").lower()


def value_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def close_key(bead: Mapping[str, Any]) -> str:
    """The closing comment's key: the bead, the close time Beads recorded, the reason's hash."""
    reason = str(bead.get("close_reason") or "")
    return (
        f"<!-- bead-mirror close bead={bead['id']} at={bead.get('closed_at') or '-'}"
        f" reason={value_hash(reason)} -->"
    )


def carries_key(body: Any, key: str) -> bool:
    return key in (line.strip() for line in str(body or "").splitlines())


def desired_state(bead: Mapping[str, Any]) -> str:
    return "CLOSED" if bead.get("status") == "closed" else "OPEN"


def parse_iso(stamp: Any) -> float | None:
    """Epoch seconds of an RFC 3339 stamp (fractions and offsets allowed), or None."""
    m = re.match(
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$",
        str(stamp or "").strip(),
    )
    if m is None:
        return None
    seconds = float(calendar.timegm(time.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")))
    zone = m.group(2) or "Z"
    if zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        digits = zone[1:].replace(":", "")
        seconds -= sign * (int(digits[:2]) * 3600 + int(digits[2:]) * 60)
    return seconds


def iso_of(seconds: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


# ---------------------------------------------------------------------------
# State helpers

STATE_MAPS = (
    "enrolled",
    "pending",
    "holds",
    "tracking",
    "retired",
    "ignored",
    "checkpoints",
)


def new_state(switch: Mapping[str, Any]) -> dict[str, Any]:
    # ``rebuild``: no complete discovery pass has run since the state was (re)made, so
    # every outbound run lists the mirror's issues until one full run completes it.
    state: dict[str, Any] = {
        "version": STATE_VERSION,
        "binding": binding_of(switch),
        "rebuild": True,
    }
    for key in STATE_MAPS:
        state[key] = {}
    return state


def shaped(state: dict[str, Any]) -> dict[str, Any]:
    for key in STATE_MAPS:
        if not isinstance(state.get(key), dict):
            state[key] = {}
    return state


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def age_seconds(stamp: Any) -> float:
    """Seconds since an ISO stamp the state recorded; unreadable counts as very old."""
    try:
        then = calendar.timegm(time.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return float("inf")
    return time.time() - then


# ---------------------------------------------------------------------------
# Subcommands


class Context:
    def __init__(
        self, mirror_dir: str, switch: dict[str, Any], lock_wait: float
    ) -> None:
        self.mirror_dir = mirror_dir
        self.switch = switch
        self.lock_wait = lock_wait
        self.env = child_env()
        self.gh = Gh(switch["host"], self.env)
        self.toplevel = ""
        digest = hashlib.sha256(mirror_dir.encode("utf-8")).hexdigest()[:12]
        self.actor = f"bead-mirror:{digest}"

    @property
    def state_path(self) -> str:
        return os.path.join(self.mirror_dir, "state.json")

    def run_checks(self) -> dict[str, Any] | None:
        """Every authority check, in order; returns the bound state or None."""
        self.toplevel = git_toplevel()
        check_store(self.switch, self.toplevel, self.env)
        check_github(self.switch, self.gh)
        state = load_state(self.mirror_dir, self.switch)
        return None if state is None else shaped(state)

    def save(self, state: Mapping[str, Any]) -> None:
        write_json_atomic(self.state_path, state)


class Outbound:
    """One outbound run: links, adoption and creation (updates and closes come later)."""

    def __init__(
        self,
        ctx: Context,
        state: dict[str, Any],
        args: argparse.Namespace,
    ) -> None:
        self.ctx = ctx
        self.state = state
        # A state rebuilt from nothing: the listing runs even if no bead is eligible for
        # a create, so an issue whose run died before linking it is still found (its
        # bead may have closed since), until one full run completes that pass.
        self.rebuilding = bool(state.get("rebuild"))
        self.dry = bool(args.dry_run)
        self.only: str | None = args.bead
        self.no_create = bool(args.no_create)
        self.report: list[str] = []
        self.planned: list[str] = []
        self.refusal: str | None = None
        self.unpublished = 0
        self.labels: dict[str, str | None] = {}
        self.store = str(ctx.switch["store_project_id"])
        self.named: dict[int, set[str]] = {}
        self.started = time.time()
        self.fresh: set[str] = set()  # created this run; the create reply was its read

    # -- bookkeeping

    def save(self) -> None:
        if not self.dry:
            self.ctx.save(self.state)

    def hold(self, bead_id: str, kind: str, reason: str) -> None:
        prev = self.state["holds"].get(bead_id)
        since = prev["since"] if prev and prev.get("kind") == kind else now_iso()
        self.state["holds"][bead_id] = {"kind": kind, "reason": reason, "since": since}

    def refuse(self, reason: str) -> None:
        if self.only:
            self.refusal = reason

    # -- the run

    def run(self) -> int:
        beads = read_beads(self.ctx.toplevel, self.ctx.env)
        if self.only and self.only not in beads:
            raise Stop(EXIT_REFUSED, f"no bead {self.only} in the store")
        self.named = issues_named(beads, self.state, self.ctx.switch)
        shared = {
            bead_id: (number, sorted(names))
            for number, names in self.named.items()
            if len(names) > 1
            for bead_id in names
        }
        for number, names in sorted({v[0]: v[1] for v in shared.values()}.items()):
            self.report.append(
                f"beads {', '.join(names)} all name issue #{number}; "
                "each is left alone until one link is fixed"
            )
        if self.only in shared:
            raise Stop(
                EXIT_REFUSED,
                f"{self.only} is not published: issue #{shared[self.only][0]} is also "
                f"named by {', '.join(b for b in shared[self.only][1] if b != self.only)}",
            )
        targets = [
            b for b in ([self.only] if self.only else sorted(beads)) if b not in shared
        ]
        for bead_id in targets:
            record = self.state["enrolled"].get(bead_id)
            if record is not None:
                self.ensure_link(bead_id, beads[bead_id], record)
        listed = [b for b in targets if self.needs_listing(b, beads[b])]
        if listed or self.rebuilding:
            found = candidates_by_bead(
                list_mirror_issues(self.ctx), self.ctx.switch["account"], self.store
            )
            # A lost state: adopt whatever the listing proves is ours.
            listed += [
                b
                for b in sorted(found)
                if b in targets
                and b not in listed
                and b not in self.state["enrolled"]
                and found[b]["live"]
            ]
            for bead_id in listed:
                if bead_id not in self.state["enrolled"]:
                    self.decide(bead_id, beads[bead_id], found.get(bead_id))
            if not self.only and not self.dry:
                self.state.pop("rebuild", None)  # every bead was offered the listing
        self.update_enrolled(beads, targets)
        if not self.only and not self.dry:
            self.state["checkpoints"]["outbound"] = iso_of(self.started)
        self.save()
        return self.finish(beads)

    # -- updates, closes and retirement of enrolled beads

    def update_enrolled(
        self, beads: Mapping[str, Mapping[str, Any]], targets: Sequence[str]
    ) -> None:
        """Touch the enrolled beads this run must: changed in Beads since the checkpoint,
        reported updated by GitHub since it, never synced, held, or awaiting a comment."""
        enrolled = self.state["enrolled"]
        if not self.only:
            for bead_id in sorted(set(enrolled) - set(beads)):
                self.report.append(
                    f"{bead_id}: enrolled issue #{enrolled[bead_id]['number']} names a "
                    "bead missing from Beads; retire it or fix the links (not retired)"
                )
        work = [b for b in targets if b in enrolled and b in beads]
        stamp = parse_iso(self.state["checkpoints"].get("outbound"))
        since = None if stamp is None else stamp - CHECKPOINT_MARGIN
        updated: set[int] = set()
        if since is not None and work and not self.only:
            updated = self.updated_since(since)
        for bead_id in work:
            bead, record = beads[bead_id], enrolled[bead_id]
            holds = self.state["holds"]
            if (bead.get("metadata") or {}).get("mirror") == "never":
                try:
                    self.retire(bead_id, record, "the bead is excluded (mirror=never)")
                except RetireFailed as exc:  # this bead only; the others still sync
                    self.hold(bead_id, "retire", f"{exc}; tried again every run")
                    self.save()
                continue
            if (holds.get(bead_id) or {}).get("kind") == "retire":
                del holds[bead_id]  # no longer excluded
            changed = parse_iso(bead.get("updated_at"))
            held = (self.state["holds"].get(bead_id) or {}).get("kind") == "open-closed"
            awaiting = desired_state(bead) == "CLOSED" and record.get(
                "comment_key"
            ) != close_key(bead)
            if bead_id in self.fresh and record.get("synced"):
                continue
            if (
                since is None
                or not record.get("synced")
                or changed is None
                or changed >= since
                or record["number"] in updated
                or held
                or awaiting
            ):
                self.sync(bead_id, bead)

    def updated_since(self, since: float) -> set[int]:
        """Numbers of the mirror's issues GitHub reports as updated since ``since``."""
        nodes = paged(
            self.ctx,
            UPDATED_QUERY,
            {
                "id": self.ctx.switch["repo_node_id"],
                "creator": self.ctx.switch["account"],
                "since": iso_of(since),
            },
            ("node", "issues"),
        )
        if nodes is None:
            raise Stop(
                EXIT_GITHUB,
                "the listing of issues updated since the last run is incomplete; "
                "enrolled issues were not updated",
            )
        return {
            n["number"]
            for n in nodes
            if isinstance(n, dict) and isinstance(n.get("number"), int)
        }

    def sync(
        self,
        bead_id: str,
        bead: Mapping[str, Any],
        force: frozenset[str] = frozenset(),
        scope: frozenset[str] = frozenset(COMPONENTS),
    ) -> None:
        """Converge one enrolled issue on its bead: text, type label, open or closed
        (by the hold table), then the closing comment. ``force`` (overwrite) names the
        components written whatever the holds and not-storable marks say; only the
        components in ``scope`` are written at all (the closing comment goes with
        ``state``)."""
        st = self.state
        record = st["enrolled"][bead_id]
        issue = read_node(self.ctx, str(record["node_id"]))
        if issue is None:
            self.report.append(
                f"{bead_id}: issue #{record['number']} cannot be read as an issue "
                "(deleted or transferred?); left alone"
            )
            return
        banner = read_banner(issue["body"])
        if (
            banner
            and banner["strict"]
            and banner["retired"]
            and banner["store"] == self.store
            and banner["bead"] == bead_id
        ):
            self.become_tracking(bead_id, record, "is marked retired on GitHub")
            return
        marks: dict[str, str] = record.setdefault("not_storable", {})
        record.pop("screened", None)
        want = {
            "title": issue_title(bead),
            "body": issue_body(self.store, bead),
            "label": LABEL_PREFIX + str(bead.get("issue_type")),
            "state": desired_state(bead),
        }
        canon = {"title": canon_title, "body": canon_body, "label": canon_label}
        screened = {}
        title_problem = screen(clean(bead.get("title")))
        if title_problem:
            screened["title"] = f"the title holds {title_problem}"
        body_problem = screen_bead(
            {k: bead.get(k) for k in ("description", "acceptance_criteria")}
        )
        if body_problem:
            screened["body"] = body_problem
        if screened:
            record["screened"] = screened

        fields: dict[str, str] = {}
        for comp in ("title", "body"):
            target = canon[comp](want[comp])
            if comp in screened or comp not in scope:
                continue
            if canon[comp](issue[comp]) == target:
                marks.pop(comp, None)
                continue
            if marks.get(comp) == value_hash(target) and comp not in force:
                continue
            marks.pop(comp, None)
            fields[comp] = want[comp]
        typed = [
            (lid, name)
            for lid, name in issue["labels"]
            if canon_label(name).startswith(LABEL_PREFIX)
        ]
        label_target = canon_label(want["label"])
        add_label = label_target not in {canon_label(n) for _, n in typed}
        remove = [(lid, n) for lid, n in typed if canon_label(n) != label_target]
        if "label" not in scope:
            add_label, remove = False, []
        elif not add_label and not remove:
            marks.pop("label", None)
        elif marks.get("label") == value_hash(label_target) and "label" not in force:
            add_label, remove = False, []
        else:
            marks.pop("label", None)
        state_write = "state" in scope and self.judge_state(
            bead_id, record, issue["state"], want["state"], force
        )

        writes: list[tuple[str, dict[str, Any], str]] = []
        if fields:
            writes.append(
                ("updateIssue", fields, f"update {', '.join(sorted(fields))}")
            )
        if add_label:
            writes.append(("addLabel", {}, f"add label {want['label']}"))
        for lid, name in remove:
            writes.append(
                (
                    "removeLabelsFromLabelable",
                    {"labelIds": [lid]},
                    f"remove label {name}",
                )
            )
        if state_write:
            mutation = "closeIssue" if want["state"] == "CLOSED" else "reopenIssue"
            writes.append((mutation, {}, mutation[: -len("Issue")]))
        if self.dry:
            self.planned += [
                f"{what} on #{record['number']} for {bead_id}" for _, _, what in writes
            ]
            return
        record["synced"] = False
        self.save()
        for mutation, payload, what in writes:
            sends_state = mutation in ("closeIssue", "reopenIssue")
            if sends_state:
                # Durable before it is sent: a lost read-back is judged next run.
                record["sent_state"] = want["state"]
                self.save()
            try:
                if mutation == "addLabel":
                    label = self.label_id(str(bead.get("issue_type")))
                    self.ctx.gh.graphql_write(
                        "addLabelsToLabelable",
                        str(record["node_id"]),
                        {"labelIds": [label]},
                        LABEL_SELECTION,
                    )
                else:
                    self.ctx.gh.graphql_write(
                        mutation,
                        str(record["node_id"]),
                        payload,
                        LABEL_SELECTION if "Label" in mutation else WRITE_SELECTION,
                    )
            except Refused as exc:
                self.report.append(
                    f"{bead_id}: GitHub refused to {what} on #{record['number']}: {exc}"
                )
                if mutation == "updateIssue":
                    for comp in payload:
                        marks[comp] = value_hash(canon[comp](payload[comp]))
                    fields = {}
                elif mutation in ("addLabel", "removeLabelsFromLabelable"):
                    marks["label"] = value_hash(label_target)
                else:
                    state_write = False
                    record.pop("sent_state", None)
                    self.hold(
                        bead_id,
                        "open-closed",
                        f"open-or-closed held: GitHub refused to {what} #{record['number']}",
                    )
            except Stop as exc:
                if sends_state and not isinstance(exc, WriteUnknown):
                    record.pop("sent_state", None)  # proven not sent: nothing to judge
                self.save()
                raise
        observed = issue["state"]
        if writes:
            observed = self.read_back(
                bead_id,
                record,
                fields,
                add_label or bool(remove),
                label_target,
                want["state"] if state_write else None,
            )
        if (
            "state" in scope
            and want["state"] == "CLOSED"
            and record.get("confirmed") == "CLOSED"
            and observed
            == "CLOSED"  # as GitHub shows it now, not an older confirmation
        ):
            try:
                self.closing_comment(bead_id, bead, record)
            except Stop:
                self.save()  # the close stays confirmed; the comment waits
                raise
        record["synced"] = True
        self.save()

    def judge_state(
        self,
        bead_id: str,
        record: dict[str, Any],
        observed: Any,
        desired: str,
        force: frozenset[str],
    ) -> bool:
        """The open-or-closed hold table; True when desired is to be written."""
        holds = self.state["holds"]
        held = (holds.get(bead_id) or {}).get("kind") == "open-closed"
        number = record["number"]
        # A value sent by an earlier run whose read-back never came: seen now, it is
        # confirmed; anything else means someone else changed it, so it holds.
        sent = record.pop("sent_state", None)
        if observed == desired:
            record["confirmed"] = desired
            if held:
                del holds[bead_id]
            return False
        if "state" in force:
            return True
        shown, wanted = str(observed).lower(), desired.lower()
        if sent is not None:
            if observed != sent:
                record["confirmed"] = None
                self.hold(
                    bead_id,
                    "open-closed",
                    f"open-or-closed held: #{number} was set {str(sent).lower()} but "
                    f"its read-back failed, and it now reads {shown} (changed on "
                    "GitHub meanwhile?); update the bead or run overwrite",
                )
                return False
            record["confirmed"] = sent
        confirmed = record.get("confirmed")
        if held:
            return False  # held until the bead agrees or the owner overwrites
        if confirmed is None:
            self.hold(
                bead_id,
                "open-closed",
                f"open-or-closed held: #{number} is {shown}, the bead wants it {wanted}, "
                "and no value was confirmed, so who changed it is unknown; "
                "update the bead or run overwrite",
            )
            return False
        if observed == confirmed:
            return True  # Beads changed
        self.hold(
            bead_id,
            "open-closed",
            f"open-or-closed held: #{number} was {shown} on GitHub against the bead "
            f"({wanted}); update the bead or run overwrite",
        )
        return False

    def read_back(
        self,
        bead_id: str,
        record: dict[str, Any],
        fields: Mapping[str, str],
        labelled: bool,
        label_target: str,
        sent_state: str | None,
    ) -> Any:
        """Read the issue after the mirror's writes: marks not-storable, confirms or
        holds; returns the open-or-closed state it read."""
        number = record["number"]
        try:
            after = read_node(self.ctx, str(record["node_id"]))
        except Stop as exc:
            after = None
            cause = str(exc)
        else:
            cause = "the issue could not be read"
        if after is None:
            self.save()
            raise Stop(
                EXIT_GITHUB,
                f"the read-back of #{number} for {bead_id} failed ({cause}); nothing "
                "was confirmed, and the next run reads it again",
            )
        marks = record.setdefault("not_storable", {})
        canon = {"title": canon_title, "body": canon_body}
        for comp, sent in fields.items():
            if canon[comp](after[comp]) != canon[comp](sent):
                marks[comp] = value_hash(canon[comp](sent))
                self.report.append(
                    f"{bead_id}: the {comp} of #{number} is not storable: GitHub kept "
                    "a different value; not rewritten until the bead changes"
                )
        if labelled:
            typed = [
                canon_label(n)
                for _, n in after["labels"]
                if canon_label(n).startswith(LABEL_PREFIX)
            ]
            if typed != [label_target]:
                marks["label"] = value_hash(label_target)
                self.report.append(
                    f"{bead_id}: the label of #{number} is not storable; not rewritten "
                    "until the bead changes"
                )
        if sent_state is None:
            # No state was sent: an earlier run's unconfirmed one stays to be judged.
            return after["state"]
        record.pop("sent_state", None)
        if after["state"] == sent_state:
            record["confirmed"] = sent_state
            self.state["holds"].pop(bead_id, None)
            return after["state"]
        record["confirmed"] = None
        self.hold(
            bead_id,
            "open-closed",
            f"open-or-closed held: #{number} was set {sent_state.lower()} but reads back "
            f"{str(after['state']).lower()} (changed on GitHub meanwhile?); not confirmed; "
            "update the bead or run overwrite",
        )
        return after["state"]

    def closing_comment(
        self, bead_id: str, bead: Mapping[str, Any], record: dict[str, Any]
    ) -> None:
        """Post the screened close reason once per close, keyed; only after the close
        is confirmed, and only after reading every comment on the issue."""
        key = close_key(bead)
        if record.get("comment_key") == key:
            return
        number = record["number"]
        posted = self.comment_posted(record, key)
        if posted is None:
            self.report.append(
                f"{bead_id}: the closing comment on #{number} waits: its comments "
                "could not all be read; retried next run"
            )
            return
        if posted:
            record["comment_key"] = key
            return
        reason = clean(bead.get("close_reason"))
        problem = screen(reason)
        if problem:
            self.report.append(
                f"{bead_id}: the close reason holds {problem}; posted as "
                '"Closed in Beads" instead'
            )
            text = "Closed in Beads."
        elif reason:
            tokens = neutral_tokens(reason)
            text = "Closed in Beads: " + cut_tokens(tokens, BODY_LIMIT - 200).rstrip()
        else:
            text = "Closed in Beads."
        self.save()
        self.ctx.gh.graphql_write(
            "addComment",
            str(record["node_id"]),
            {"body": key + "\n" + text},
            "clientMutationId",
        )
        # The key is recorded only once the comment is seen on the issue; until then
        # every run reads the comments first, so a comment that did land is not repeated.
        if not self.comment_posted(record, key):
            self.report.append(
                f"{bead_id}: the closing comment on #{number} was sent but is not "
                "shown on the issue; retried next run"
            )
            return
        record["comment_key"] = key
        self.save()
        self.report.append(f"{bead_id}: posted the closing comment on #{number}")

    def comment_posted(self, record: Mapping[str, Any], key: str) -> bool | None:
        """Whether a comment by the mirror account carries ``key`` on a line of its own;
        None when the comments could not all be read."""
        comments = paged(
            self.ctx, COMMENTS_QUERY, {"id": record["node_id"]}, ("node", "comments")
        )
        if comments is None:
            return None
        account = self.ctx.switch["account"]
        return any(
            isinstance(c, dict)
            and ((c.get("author") or {}).get("login") == account)
            and carries_key(c.get("body"), key)
            for c in comments
        )

    def become_tracking(
        self, bead_id: str, record: Mapping[str, Any], why: str
    ) -> None:
        st = self.state
        st["enrolled"].pop(bead_id, None)
        st["holds"].pop(bead_id, None)
        st["tracking"][bead_id] = record["number"]
        st["retired"][bead_id] = record["number"]
        self.save()
        self.report.append(f"{bead_id}: issue #{record['number']} {why}; tracking-only")

    def retire(self, bead_id: str, record: Mapping[str, Any], why: str) -> None:
        """Mark the banner retired: the last write to the issue; Stop if it fails."""
        number = record["number"]
        issue = read_node(self.ctx, str(record["node_id"]))
        banner = read_banner(issue["body"]) if issue else None
        if (
            issue is None
            or banner is None
            or not banner["strict"]
            or banner["store"] != self.store
            or banner["bead"] != bead_id
        ):
            raise RetireFailed(
                f"retiring #{number} for {bead_id} failed: its body has no banner of "
                "this store and bead to mark; it stays managed",
            )
        if banner["retired"]:
            self.become_tracking(bead_id, record, "is already retired")
            return
        rest = issue["body"].lstrip("﻿").split("\n", 1)
        body = banner_line(self.store, bead_id, retired=True) + (
            "\n" + rest[1] if len(rest) > 1 else ""
        )
        if self.dry:
            self.planned.append(f"retire #{number} for {bead_id} ({why})")
            return
        try:
            self.ctx.gh.graphql_write(
                "updateIssue", str(record["node_id"]), {"body": body}, WRITE_SELECTION
            )
            after = read_node(self.ctx, str(record["node_id"]))
        except Refused as exc:
            raise RetireFailed(
                f"retiring #{number} for {bead_id} failed: {exc}; it stays managed"
            ) from exc
        except Stop as exc:
            raise Stop(
                exc.code,
                f"retiring #{number} for {bead_id} failed: {exc}; it stays managed",
            ) from exc
        check = read_banner(after["body"]) if after else None
        if not (
            check and check["strict"] and check["retired"] and check["bead"] == bead_id
        ):
            raise RetireFailed(
                f"retiring #{number} for {bead_id} failed: the read-back shows no "
                "retired banner; it stays managed",
            )
        self.become_tracking(bead_id, record, f"retired ({why})")

    def needs_listing(self, bead_id: str, bead: Mapping[str, Any]) -> bool:
        """Classify one bead before any listing; True when the listing must decide it."""
        st = self.state
        if bead_id in st["enrolled"]:
            return False
        held = st["holds"].get(bead_id)
        if held and held.get("kind") == "screen":
            del st["holds"][bead_id]  # recomputed below
            held = None
        if bead_id in st["pending"] or held:
            return True
        if (bead.get("metadata") or {}).get("mirror") == "never":
            self.refuse("the bead is excluded (mirror=never)")
            return False
        ref = str(bead.get("external_ref") or "").strip()
        if ref:
            number = issue_number_in(ref, self.ctx.switch)
            if number is None:
                self.refuse(f"the bead links outside this repository ({ref})")
                return False
            return bool(st["tracking"].get(bead_id) != number)
        why = self.not_creatable(bead)
        if why:
            self.refuse(why)
            return False
        problem = screen_bead(bead)
        if problem:
            self.hold(bead_id, "screen", f"not published: {problem}")
            return False
        if self.no_create:
            self.unpublished += 1
            return False
        return True

    def not_creatable(self, bead: Mapping[str, Any]) -> str | None:
        status = bead.get("status")
        if status not in ELIGIBLE_STATUSES:
            if status == "closed":
                return "the bead is closed and was never published"
            return f"the bead's status is {status}"
        kind = bead.get("issue_type")
        if kind not in self.ctx.switch["scope"]:
            if self.only and self.ctx.switch["pr_enrol"]:
                return None
            if self.only:
                return f"type {kind} is outside the switch's scope and pr_enrol is off"
            return f"type {kind} is outside the switch's scope"
        return None

    def decide(
        self,
        bead_id: str,
        bead: Mapping[str, Any],
        found: Mapping[str, list[dict[str, Any]]] | None,
    ) -> None:
        """Adopt, hold, wait or create, from a complete listing."""
        st = self.state
        prev = st["holds"].pop(bead_id, None)
        if prev and prev.get("kind") != "screen":
            prev = None
        if prev:
            st["holds"][bead_id] = prev
        ignored = set(st["ignored"].get(bead_id, []))
        found = found or {"live": [], "foreign": [], "retired": []}
        live = [c for c in found["live"] if c["number"] not in ignored]
        foreign = [c for c in found["foreign"] if c["number"] not in ignored]
        retired = [c for c in found["retired"] if c["number"] not in ignored]
        if len(live) == 1 and not foreign:
            others = sorted(self.named.get(live[0]["number"], set()) - {bead_id})
            if others:  # adopting would make two beads name one issue
                self.hold(
                    bead_id,
                    "candidates",
                    f"create held: the mirror's issue #{live[0]['number']} names this "
                    f"bead but {', '.join(others)} already links it; run resolve",
                )
                self.refuse("its issue is already named by another bead")
                return
            self.adopt(bead_id, bead, live[0])
            return
        if live or foreign:
            numbers = ", ".join(
                f"#{c['number']}"
                for c in sorted(live + foreign, key=lambda c: c["number"])
            )
            self.hold(
                bead_id,
                "candidates",
                f"create held: mirror-authored issues {numbers} name this bead "
                "(several, or another store); run resolve",
            )
            return
        if retired:
            st["tracking"][bead_id] = retired[0]["number"]
            st["retired"][bead_id] = retired[0]["number"]
            st["pending"].pop(bead_id, None)
            self.report.append(
                f"{bead_id}: issue #{retired[0]['number']} is retired; tracking-only"
            )
            return
        pending = st["pending"].get(bead_id)
        if pending is not None:
            if age_seconds(pending.get("since")) > PENDING_HOLD_SECONDS:
                self.hold(
                    bead_id,
                    "pending",
                    f"create held: an attempt sent {pending.get('since')} has not "
                    "appeared in the listing; run resolve",
                )
            else:
                self.report.append(
                    f"{bead_id}: waiting for the create sent {pending.get('since')} "
                    "to appear in the listing; nothing is sent again"
                )
            self.refuse("its create is pending")
            return
        ref = str(bead.get("external_ref") or "").strip()
        if ref:
            number = issue_number_in(ref, self.ctx.switch)
            if number is None:
                return
            issue, why = checked_issue(self.ctx, number)
            if issue is None:  # what `link` would refuse is not tracked either
                st["tracking"].pop(bead_id, None)
                self.hold(bead_id, "bad-link", f"not tracked: {why}; fix the link")
                return
            st["tracking"][bead_id] = number
            return
        if (bead.get("metadata") or {}).get("mirror") == "never" or self.not_creatable(
            bead
        ):
            return
        problem = screen_bead(bead)
        if problem:
            self.hold(bead_id, "screen", f"not published: {problem}")
            return
        if self.no_create:
            self.unpublished += 1
            return
        self.create(bead_id, bead)

    # -- writes

    def adopt(
        self, bead_id: str, bead: Mapping[str, Any], issue: Mapping[str, Any]
    ) -> None:
        ref = str(bead.get("external_ref") or "").strip()
        if (
            ref
            and ref != issue["url"]
            and issue_number_in(ref, self.ctx.switch) != issue["number"]
        ):
            self.state["pending"].pop(bead_id, None)
            self.hold(
                bead_id,
                "link-conflict",
                f"link conflict: the bead links {ref}; the mirror's issue "
                f"#{issue['number']} is left unlinked",
            )
            return
        if self.dry:
            self.planned.append(f"adopt #{issue['number']} for {bead_id}")
            return
        self.state["enrolled"][bead_id] = {
            k: issue[k] for k in ("number", "node_id", "url")
        }
        for key in ("pending", "tracking", "retired", "holds"):
            self.state[key].pop(bead_id, None)
        self.save()
        self.report.append(f"{bead_id}: adopted #{issue['number']} {issue['url']}")
        self.link(bead_id, issue["url"], issue["number"])

    def ensure_link(
        self, bead_id: str, bead: Mapping[str, Any], record: dict[str, Any]
    ) -> None:
        """Link an enrolled bead whose link is missing (a run died before writing it).
        The cached URL is not trusted: the issue is read by node ID first, and linked by
        its current URL only while it is still an issue in the switch's repository."""
        ref = str(bead.get("external_ref") or "").strip()
        if (
            ref == record["url"]
            or issue_number_in(ref, self.ctx.switch) == record["number"]
        ):
            return
        issue = read_node(self.ctx, str(record["node_id"]))
        if issue is None:
            self.report.append(
                f"{bead_id}: issue #{record['number']} cannot be read as an issue in "
                f"{self.ctx.switch['repo']} (deleted or transferred?); not linked"
            )
            return
        record["number"], record["url"] = issue["number"], issue["url"]
        if self.dry:
            self.planned.append(f"link {bead_id} to {issue['url']}")
            return
        self.save()
        self.link(bead_id, str(issue["url"]), int(issue["number"]))

    def link(self, bead_id: str, url: str, number: int) -> None:
        outcome, found = write_link(self.ctx, bead_id, url, number, self.ctx.actor)
        if outcome == "conflict":
            self.state["enrolled"].pop(bead_id, None)
            self.hold(
                bead_id,
                "link-conflict",
                f"link conflict: the bead links {found}; the mirror's issue "
                f"#{number} is left unlinked",
            )
            self.save()
        elif outcome == "written":
            self.report.append(f"{bead_id}: linked {url}")

    def label_id(self, kind: str) -> str | None:
        """The ``bead-type:`` label's node ID, created on the repository if missing."""
        name = LABEL_PREFIX + kind
        if name in self.labels:
            return self.labels[name]
        repo = self.ctx.switch["repo_node_id"]
        data = self.ctx.gh.graphql(LABEL_QUERY, {"id": repo, "name": name})
        label = (data.get("node") or {}).get("label")
        if isinstance(label, dict) and looks_like_node_id(label.get("id")):
            self.labels[name] = str(label["id"])
        elif self.dry:
            self.planned.append(f"create label {name}")
            self.labels[name] = None
        else:
            made = self.ctx.gh.graphql_write(
                "createLabel",
                repo,
                {"name": name, "color": LABEL_COLOR},
                "label { id name }",
            )
            label = made.get("label") if isinstance(made, dict) else None
            if not isinstance(label, dict) or not looks_like_node_id(label.get("id")):
                raise Stop(EXIT_GITHUB, f"GitHub did not return the new label {name}")
            self.labels[name] = str(label["id"])
        return self.labels[name]

    def create(self, bead_id: str, bead: Mapping[str, Any]) -> None:
        try:
            label = self.label_id(str(bead.get("issue_type")))
        except Refused as exc:  # this bead's label: hold it, create the others
            self.hold(bead_id, "refused", f"create refused: {exc}")
            self.save()
            self.refuse(f"GitHub refused its label: {exc}")
            return
        if self.dry:
            self.planned.append(f"create an issue for {bead_id}")
            return
        st = self.state
        st["pending"][bead_id] = {"since": now_iso()}
        self.save()  # durable before the create is sent
        fields = {
            "title": issue_title(bead),
            "body": issue_body(self.store, bead),
            "labelIds": [label],
        }
        try:
            made = self.ctx.gh.graphql_write(
                "createIssue", self.ctx.switch["repo_node_id"], fields, CREATE_SELECTION
            )
        except WriteUnknown as exc:
            raise Stop(
                EXIT_GITHUB,
                f"{exc}; bead {bead_id} has a pending create, and later runs adopt "
                "its issue from the listing instead of sending another",
            ) from exc
        except Refused as exc:  # this bead's input: hold it, create the others
            st["pending"].pop(bead_id, None)  # GitHub created nothing
            self.hold(bead_id, "refused", f"create refused: {exc}")
            self.save()
            self.refuse(f"GitHub refused its create: {exc}")
            return
        except Stop:
            st["pending"].pop(bead_id, None)  # GitHub created nothing
            self.save()
            raise
        issue = as_issue(made.get("issue"))
        if issue is None:
            raise Stop(
                EXIT_GITHUB,
                f"createIssue for {bead_id} returned no issue; it stays pending",
            )
        record: dict[str, Any] = {k: issue[k] for k in ("number", "node_id", "url")}
        # The reply is the first read-back: it confirms the state and shows what was stored.
        record["confirmed"] = "OPEN" if issue["state"] == "OPEN" else None
        record["not_storable"] = {
            comp: value_hash(canon(fields[comp]))
            for comp, canon, got in (
                ("title", canon_title, (made.get("issue") or {}).get("title")),
                ("body", canon_body, issue["body"]),
            )
            if canon(got) != canon(fields[comp])
        }
        record["synced"] = record["confirmed"] == "OPEN"
        st["enrolled"][bead_id] = record
        self.fresh.add(bead_id)
        st["pending"].pop(bead_id, None)
        self.save()  # the number is recorded at once
        self.report.append(f"{bead_id}: created #{issue['number']} {issue['url']}")
        self.link(bead_id, issue["url"], issue["number"])

    # -- the report

    def finish(self, beads: Mapping[str, Mapping[str, Any]]) -> int:
        out = [
            "bead-mirror: dry run, checks passed, nothing written"
            if self.dry
            else "bead-mirror: outbound: checks passed"
        ]
        out += ["  " + line for line in self.report]
        holds = self.state["holds"]
        shown = [self.only] if self.only else sorted(holds)
        out += [f"  held: {b}: {holds[b]['reason']}" for b in shown if b in holds]
        enrolled = self.state["enrolled"]
        for b in [self.only] if self.only else sorted(enrolled):
            record = enrolled.get(b) or {}
            for comp, why in sorted((record.get("screened") or {}).items()):
                out.append(f"  held: {b}: the {comp} update is not published: {why}")
            marks = sorted(record.get("not_storable") or {})
            if marks:
                out.append(
                    f"  not storable: {b}: {', '.join(marks)} of #{record['number']} "
                    "(GitHub keeps a different value; rewritten when the bead changes)"
                )
        if self.unpublished:
            out.append(
                f"  {self.unpublished} eligible bead(s) not yet published; "
                "run outbound in the foreground to create them"
            )
        if self.dry:
            sw = self.ctx.switch
            out.append(f"  store: {sw['store_project_id']}")
            out.append(
                f"  repository: {sw['repo']} on {sw['host']} ({sw['repo_node_id']})"
            )
            out.append(f"  account: {sw['account']}")
            if self.planned:
                out.append("  planned writes:")
                out += ["    " + p for p in self.planned]
            else:
                out.append("  planned writes: none")
        print("\n".join(out))
        if not self.only:
            return EXIT_OK
        # The pr path reports an issue only from a fresh read bound to the repository:
        # a URL the state cached may name an issue deleted or transferred since.
        record = self.state["enrolled"].get(self.only)
        if record is not None:
            issue = read_node(self.ctx, str(record["node_id"]))
            if issue is None:
                raise Stop(
                    EXIT_REFUSED,
                    f"{self.only} is not published: its issue #{record['number']} "
                    f"cannot be read as an issue in {self.ctx.switch['repo']} "
                    "(deleted or transferred?)",
                )
            print(issue["url"])
            return EXIT_OK
        ref = str(beads[self.only].get("external_ref") or "").strip()
        number = issue_number_in(ref, self.ctx.switch)
        if (
            number is not None
            and self.state["tracking"].get(self.only) == number
            and self.only not in holds
        ):
            issue, why = checked_issue(self.ctx, number)
            if issue is None:
                raise Stop(EXIT_REFUSED, f"{self.only} is not tracked: {why}")
            print(issue["url"])  # a tracking-only link, checked now
            return EXIT_OK
        if self.dry and any(self.only in p for p in self.planned):
            return EXIT_OK
        held = holds.get(self.only)
        reason = held["reason"] if held else self.refusal or "it has no issue"
        raise Stop(EXIT_REFUSED, f"{self.only} is not published: {reason}")


def cmd_outbound(ctx: Context, args: argparse.Namespace) -> int:
    if args.dry_run:
        state = ctx.run_checks()
        return Outbound(ctx, state or new_state(ctx.switch), args).run()
    with CloneLock(ctx.mirror_dir, ctx.lock_wait):
        bound = ctx.run_checks()
        if bound is None:
            bound = new_state(ctx.switch)
            ctx.save(bound)
        return Outbound(ctx, bound, args).run()


def cmd_link(ctx: Context, args: argparse.Namespace) -> int:
    actor = args.actor.strip()
    if not actor or args.number <= 0:
        raise Stop(
            EXIT_REFUSED, "link needs a bead, a positive issue number and --actor"
        )
    with CloneLock(ctx.mirror_dir, ctx.lock_wait):
        state = ctx.run_checks()
        beads = read_beads(ctx.toplevel, ctx.env)
        if args.bead not in beads:
            raise Stop(EXIT_REFUSED, f"no bead {args.bead} in the store")
        others = sorted(
            issues_named(beads, state, ctx.switch).get(args.number, set()) - {args.bead}
        )
        if others:
            raise Stop(
                EXIT_REFUSED,
                f"#{args.number} is already named by {', '.join(others)}; "
                "two beads naming one issue are left alone, so nothing was written",
            )
        issue, problem = checked_issue(ctx, args.number)
        if issue is None:
            raise Stop(EXIT_REFUSED, problem)
        url = str(issue["url"])
        outcome, found = write_link(ctx, args.bead, url, args.number, actor)
    if outcome == "conflict":
        raise Stop(
            EXIT_REFUSED,
            f"link conflict: {args.bead} already links {found}; left as it is",
        )
    verb = "linked" if outcome == "written" else "already linked"
    print(f"bead-mirror: {args.bead} {verb} to {url}")
    return EXIT_OK


# The holds `resolve --create` releases: a create held for candidates or left pending.
CREATE_HOLDS = ("candidates", "pending")


def cmd_resolve(ctx: Context, args: argparse.Namespace) -> int:
    with CloneLock(ctx.mirror_dir, ctx.lock_wait):
        state = ctx.run_checks() or new_state(ctx.switch)
        beads = read_beads(ctx.toplevel, ctx.env)
        bead = beads.get(args.bead)
        if bead is None:
            raise Stop(EXIT_REFUSED, f"no bead {args.bead} in the store")
        if args.bead in state["enrolled"]:
            number = state["enrolled"][args.bead]["number"]
            raise Stop(EXIT_REFUSED, f"{args.bead} is already enrolled as #{number}")
        store, account = str(ctx.switch["store_project_id"]), ctx.switch["account"]
        found = candidates_by_bead(list_mirror_issues(ctx), account, store).get(
            args.bead, {}
        )
        seen = {
            c["number"] for kind in ("live", "foreign") for c in found.get(kind, [])
        }
        if args.create:
            held = (state["holds"].get(args.bead) or {}).get("kind")
            if args.bead not in state["pending"] and held not in CREATE_HOLDS:
                raise Stop(
                    EXIT_REFUSED,
                    f"{args.bead} has no held create to release; outbound decides it",
                )
            ignored = set(state["ignored"].get(args.bead, []))
            live = [c for c in found.get("live", []) if c["number"] not in ignored]
            foreign = [
                c for c in found.get("foreign", []) if c["number"] not in ignored
            ]
            if len(live) == 1 and not foreign:
                raise Stop(
                    EXIT_REFUSED,
                    f"the mirror's issue #{live[0]['number']} is {args.bead}'s; a fresh "
                    f"create would duplicate it: run resolve --adopt {live[0]['number']}",
                )
            state["pending"].pop(args.bead, None)
            state["holds"].pop(args.bead, None)
            state["ignored"][args.bead] = sorted(
                set(state["ignored"].get(args.bead, [])) | seen
            )
            ctx.save(state)
            print(
                f"bead-mirror: {args.bead} released; the next foreground outbound run "
                "may create its issue"
            )
            return EXIT_OK
        issue = as_issue(fetch_issue(ctx, args.adopt))
        banner = read_banner(issue["body"]) if issue else None
        if (
            issue is None
            or issue["author"] != account
            or banner is None
            or not banner["strict"]
            or banner["store"] != store
            or banner["bead"] != args.bead
            or banner["retired"]
        ):
            raise Stop(
                EXIT_REFUSED,
                f"#{args.adopt} is not a live issue the mirror account created for "
                f"{args.bead} in this store",
            )
        ref = str(bead.get("external_ref") or "").strip()
        if ref and issue_number_in(ref, ctx.switch) != issue["number"]:
            raise Stop(EXIT_REFUSED, f"link conflict: {args.bead} already links {ref}")
        others = sorted(
            issues_named(beads, state, ctx.switch).get(issue["number"], set())
            - {args.bead}
        )
        if others:
            raise Stop(
                EXIT_REFUSED,
                f"#{issue['number']} is already named by {', '.join(others)}; "
                "two beads naming one issue are left alone, so nothing was written",
            )
        state["enrolled"][args.bead] = {
            k: issue[k] for k in ("number", "node_id", "url")
        }
        for key in ("pending", "holds", "tracking", "retired"):
            state[key].pop(args.bead, None)
        state["ignored"][args.bead] = sorted(seen - {issue["number"]})
        ctx.save(state)
        outcome, found_ref = write_link(
            ctx, args.bead, issue["url"], issue["number"], ctx.actor
        )
        if outcome == "conflict":
            state["enrolled"].pop(args.bead, None)
            ctx.save(state)
            raise Stop(
                EXIT_REFUSED, f"link conflict: {args.bead} already links {found_ref}"
            )
    print(f"bead-mirror: {args.bead} adopted #{issue['number']} {issue['url']}")
    return EXIT_OK


def cmd_reset_state(ctx: Context, args: argparse.Namespace) -> int:
    with CloneLock(ctx.mirror_dir, ctx.lock_wait):
        try:
            os.unlink(ctx.state_path)
        except FileNotFoundError:
            print("bead-mirror: no state to reset")
            return EXIT_OK
        fsync_dir(ctx.mirror_dir)
    print("bead-mirror: state discarded; the next run rebuilds it")
    return EXIT_OK


def refuse_shared(
    ctx: Context,
    beads: Mapping[str, Mapping[str, Any]],
    state: Mapping[str, Any],
    bead_id: str,
    number: int,
) -> None:
    """Stop when another bead also names issue ``number``: outbound leaves such beads
    alone, and so do the manual writes."""
    others = sorted(
        issues_named(beads, state, ctx.switch).get(number, set()) - {bead_id}
    )
    if others:
        raise Stop(
            EXIT_REFUSED,
            f"#{number} is also named by {', '.join(others)}; two beads naming one "
            "issue are left alone until one link is fixed, so nothing was written",
        )


def single(ctx: Context, state: dict[str, Any], bead_id: str) -> Outbound:
    """An Outbound run limited to one bead, for overwrite and retire."""
    args = argparse.Namespace(dry_run=False, bead=bead_id, no_create=True)
    return Outbound(ctx, state, args)


def cmd_overwrite(ctx: Context, args: argparse.Namespace) -> int:
    with CloneLock(ctx.mirror_dir, ctx.lock_wait):
        state = ctx.run_checks() or new_state(ctx.switch)
        beads = read_beads(ctx.toplevel, ctx.env)
        bead = beads.get(args.bead)
        if bead is None:
            raise Stop(EXIT_REFUSED, f"no bead {args.bead} in the store")
        if args.bead not in state["enrolled"]:
            raise Stop(
                EXIT_REFUSED,
                f"{args.bead} is not enrolled; only the mirror's own issues are written",
            )
        if (bead.get("metadata") or {}).get("mirror") == "never":
            raise Stop(
                EXIT_REFUSED,
                f"{args.bead} is excluded (mirror=never); outbound retires it",
            )
        refuse_shared(
            ctx, beads, state, args.bead, int(state["enrolled"][args.bead]["number"])
        )
        run = single(ctx, state, args.bead)
        named = frozenset([args.component] if args.component else COMPONENTS)
        run.sync(args.bead, bead, force=named, scope=named)
        run.save()
    record = state["enrolled"].get(args.bead) or {}
    out = [f"bead-mirror: overwrite {args.bead} #{record.get('number')}"]
    out += ["  " + line for line in run.report]
    held = state["holds"].get(args.bead)
    if held:
        out.append(f"  held: {args.bead}: {held['reason']}")
    print("\n".join(out))
    return EXIT_OK


def cmd_retire(ctx: Context, args: argparse.Namespace) -> int:
    with CloneLock(ctx.mirror_dir, ctx.lock_wait):
        state = ctx.run_checks() or new_state(ctx.switch)
        beads = read_beads(ctx.toplevel, ctx.env)
        record = state["enrolled"].get(args.bead)
        if record is None:
            # A lost state: the bead's link may still name the mirror's issue.
            bead = beads.get(args.bead) or {}
            number = issue_number_in(str(bead.get("external_ref") or ""), ctx.switch)
            issue = as_issue(fetch_issue(ctx, number)) if number else None
            if issue is None or issue["author"] != ctx.switch["account"]:
                raise Stop(
                    EXIT_REFUSED,
                    f"{args.bead} has no issue the mirror account created to retire",
                )
            record = {k: issue[k] for k in ("number", "node_id", "url")}
        refuse_shared(ctx, beads, state, args.bead, int(record["number"]))
        state["enrolled"][args.bead] = record
        run = single(ctx, state, args.bead)
        run.retire(args.bead, record, "by the owner")
    print(f"bead-mirror: {args.bead}: " + "; ".join(run.report))
    return EXIT_OK


def cmd_map(ctx: Context, args: argparse.Namespace) -> int:
    """Bead <-> issue from the state and the links; reads only, no GitHub call."""
    ctx.toplevel = git_toplevel()
    check_store(ctx.switch, ctx.toplevel, ctx.env)
    state = shaped(load_state(ctx.mirror_dir, ctx.switch) or new_state(ctx.switch))
    beads = read_beads(ctx.toplevel, ctx.env)
    rows: dict[str, tuple[Any, str, str]] = {}
    for bead_id, bead in beads.items():
        ref = str(bead.get("external_ref") or "").strip()
        number = issue_number_in(ref, ctx.switch)
        if number is not None:
            rows[bead_id] = (number, ref, "linked")
    for bead_id, number in state["tracking"].items():
        url = rows.get(bead_id, (None, "", ""))[1]
        rows[bead_id] = (number, url, "tracking-only")
    for bead_id, record in state["enrolled"].items():
        kind = "enrolled" if bead_id in beads else "enrolled, bead missing"
        rows[bead_id] = (record["number"], str(record["url"]), kind)
    for bead_id in state["pending"]:
        rows.setdefault(bead_id, ("?", "", "create pending"))
    print("bead-mirror: map (bead, issue, link, kind)")
    for bead_id in sorted(rows):
        number, url, kind = rows[bead_id]
        print(f"  {bead_id}\t#{number}\t{url or '-'}\t{kind}")
    return EXIT_OK


COMMANDS = {
    "outbound": cmd_outbound,
    "link": cmd_link,
    "resolve": cmd_resolve,
    "reset-state": cmd_reset_state,
    "overwrite": cmd_overwrite,
    "retire": cmd_retire,
    "map": cmd_map,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bead-mirror", description=__doc__.splitlines()[0]
    )
    parser.add_argument(
        "--lock-wait",
        type=float,
        default=DEFAULT_LOCK_WAIT,
        metavar="SECONDS",
        help="how long to wait for the clone-wide lock before reporting busy",
    )
    sub = parser.add_subparsers(dest="command", metavar="SUBCOMMAND")
    sub.required = True
    out = sub.add_parser("outbound", help="publish beads to GitHub")
    out.add_argument(
        "--dry-run", action="store_true", help="run every check; report; write nothing"
    )
    out.add_argument(
        "--bead", metavar="ID", help="enrol and publish this bead only (the pr path)"
    )
    out.add_argument("--no-create", action="store_true", help="never create an issue")
    link = sub.add_parser(
        "link", help="record a tracking-only link, if the field is empty"
    )
    link.add_argument("bead")
    link.add_argument("number", type=int)
    link.add_argument("--actor", required=True, help="the calling agent's Beads actor")
    resolve = sub.add_parser("resolve", help="release a held create for one bead")
    resolve.add_argument("bead")
    choice = resolve.add_mutually_exclusive_group(required=True)
    choice.add_argument("--adopt", type=int, metavar="NUMBER", help="adopt this issue")
    choice.add_argument("--create", action="store_true", help="allow a fresh create")
    sub.add_parser("reset-state", help="discard the state so the next run rebuilds it")
    over = sub.add_parser(
        "overwrite", help="read one enrolled issue fresh and write the bead's values"
    )
    over.add_argument("bead")
    over.add_argument("component", nargs="?", choices=COMPONENTS)
    ret = sub.add_parser(
        "retire", help="stop managing a bead's issue, marked on GitHub"
    )
    ret.add_argument("bead")
    sub.add_parser("map", help="print bead <-> issue from the state and the links")
    for name in LATER_STAGES:
        sub.add_parser(name, help="(not implemented yet)")
    return parser


def fail(code: int, message: str) -> NoReturn:
    print("bead-mirror: " + message, file=sys.stderr)
    raise SystemExit(code)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    common = git_common_dir()
    mirror_dir = os.path.join(common, MIRROR_DIRNAME) if common else ""
    try:
        switch = load_switch(mirror_dir) if common else None
        # No switch is silent even for malformed arguments; only help still answers.
        if switch is None and not {"-h", "--help"} & set(argv):
            return EXIT_OK
        args = build_parser().parse_args(argv)
        if switch is None:
            return EXIT_OK
        if args.command in LATER_STAGES:
            raise Stop(EXIT_NOT_IMPLEMENTED, f"{args.command}: not implemented")
        ctx = Context(mirror_dir, switch, args.lock_wait)
        return COMMANDS[args.command](ctx, args)
    except Stop as stop:
        fail(stop.code, str(stop))


if __name__ == "__main__":
    sys.exit(main())
