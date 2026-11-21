"""A small stateful GitHub simulator, run as ``gh`` by the mirror tests.

The fixture writes a wrapper named ``gh`` that sets ``FAKE_GH_STATE`` to a JSON file
and runs this script. The state holds the host, the authenticated login, repositories
(node ID, owner, name, labels, issues, pull requests) and the fault switches; every
call is appended to ``calls`` and every call this fake does not recognise to
``unrecognised`` (it then fails loudly with exit 99). Responses are shaped by the
provisional fixtures beside this file. It never touches the network.

Routes: ``GET user``; ``GET repos/OWNER/NAME``; ``GET repos/OWNER/NAME/pulls/N`` (a
pull request's author and current body, as the check's workflow reads it); GraphQL queries ``MirrorIssues`` (the
repository's issues filtered by creator and by the query's ``states``, as GitHub filters
them; every state when it names none; paginated), ``MirrorLabel`` and ``MirrorIssue``
(one issue or pull request by number), ``MirrorUpdated`` (the creator's issues updated
at or after ``since``), all addressed by the repository's node ID; ``MirrorIssueNode``
(one issue with title and labels) and ``MirrorComments`` (its comments, paginated), by
the issue's node ID; the mutations ``createIssue``, ``createLabel``, ``updateIssue``,
``closeIssue``, ``reopenIssue``, ``addComment``, ``addLabelsToLabelable`` and
``removeLabelsFromLabelable``. Every issue keeps ``updated_at``, stamped by each write.
Each query's text must have the shape ``QUERY_SHAPES`` records (its argument bindings
and the names it uses), and each mutation its input type, input fields and selection
(``MUTATION_SHAPES``); anything else is unrecognised, as GitHub would reject it.

Inbound routes, by the repository's node ID: ``MirrorInboundIssues`` (every author's
issues updated at or after ``since``, by number, paginated), ``MirrorInboundPulls``
(every pull request, most recently updated first, paginated), ``MirrorHighWater`` (the
newest issue and pull request) and ``MirrorItem`` (one issue or pull request by number,
with the fields inbound reads); ``MirrorClosedBy`` (an issue's latest closing event:
the merged pull request or commit that closed it, or none when closed by hand), by the
issue's node ID. Issues keep ``closed_at`` and ``closing_events`` ([{"at", "closer":
{"pull": N, "repo"?: "owner/name" of another repository} | {"commit": SHA} | null}]); pull requests keep ``state`` (OPEN, CLOSED,
MERGED), ``merged_at``, ``merged_by``, ``merge_commit`` and ``updated_at``.

Faults (``state["faults"]``): ``unauthenticated``; ``rate_limited`` (403 or 429, with
the rate headers under ``--include``); ``offline``; ``delay`` (seconds slept before
answering, for lock tests); ``rename_after_check`` ({"repo_node_id", "new_name",
"squatter_node_id"}: after the first successful ``repos/OWNER/NAME`` read of that
repository, it is renamed and another repository takes the old name);
``lose_create_response`` (the issue is created, the reply is lost); ``listing_lag``
(a new issue stays out of the next N complete listings); ``close_created`` (a new issue
is closed at once, as if a collaborator closed it before recovery); ``hang_after_create``
(seconds slept after creating, before replying, so a test can kill the caller);
``failed_page`` (that 1-based page of the issues listing fails with HTTP 502);
``page_size`` (the most issues one listing page returns); ``ignore_creator_filter``
(the listing returns every author's issues, as a changed API might);
``error_after_create`` (the issue is created, the reply is GraphQL's generic
"Something went wrong" error, or the ``errors.json`` entry the fault names, such as
``field_error_after_write``: a selected field failed after the create); ``refuse_create_titled`` (a create whose title contains
that text is rejected as unprocessable); ``fail_create`` (``offline``,
``unauthenticated`` or ``rate_limited_429``: only ``createIssue`` fails that way,
before creating anything); ``refuse_label`` (a ``createLabel`` whose name contains
that text is rejected as unprocessable); ``drop_write`` (a list of mutation names:
GitHub answers success and keeps nothing); ``interrupt_readback`` (the first
``MirrorIssueNode`` read after a write fails with HTTP 502, or the ``errors.json`` entry
it names, once);
``collaborator_after_write`` ({mutation: {field: value}}: right after that write, a
collaborator sets those issue fields, once); ``stores_body_as`` ([old, new]: GitHub
stores every body with ``old`` replaced by ``new``); ``fail_write`` ({mutation: an
``errors.json`` name}); ``failed_comments_page`` and ``comments_page_size``; ``malformed_page`` ({"page": N,
"kind": "no_has_next" | "stuck_cursor"}: that issues-listing page omits
``hasNextPage``, or says another page follows with the cursor it was asked from) and
``malformed_comments_page`` (that comments page omits ``hasNextPage``); ``malformed_pull``
(``not_json``, ``no_user`` or ``no_body``: the pull-request read returns no JSON, no
author, or no ``body`` key); ``fail_query``
({operation: an ``errors.json`` name}: that query fails that way, after the checks);
``failed_inbound_page`` ({"op": an inbound listing, "page": N}: that page fails with
HTTP 502, after the earlier pages answered); ``failed_timeline`` (issue numbers whose
closing-event read fails with HTTP 502); ``open_after_high_water`` (a login that opens
an issue right after the high-water read); ``instruction_titles`` (text served as every
inbound issue's and pull request's ``title``, unasked, and appended to pull-request
bodies). A comment
carrying a copied key is seeded with ``Fake.add_comment``. Titles over 256 characters are always rejected,
as GitHub does. A wrong login is just a
different ``login``; ``gh`` missing is a PATH without this fake. Issues copied by
another author or naming another store are seeded straight into the state
(``Fake.add_issue`` in the harness).
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "provisional"
UNRECOGNISED_EXIT = 99
KNOWN_FLAGS_WITH_VALUE = {"--hostname", "--input"}
KNOWN_BOOL_FLAGS = {"-i", "--include"}
MUTATION_RE = re.compile(r"^\s*mutation\b[^{]*\{\s*(\w+)\(input:\s*\$input\)")
QUERY_RE = re.compile(r"^\s*query\s+(\w+)\(")
QUERIES = {
    "MirrorIssues": {"id", "creator", "first"},
    "MirrorLabel": {"id", "name"},
    "MirrorIssue": {"id", "number"},
    "MirrorIssueNode": {"id"},
    "MirrorUpdated": {"id", "creator", "first", "since"},
    "MirrorComments": {"id", "first"},
    "MirrorInboundIssues": {"id", "since", "first"},
    "MirrorInboundPulls": {"id", "first"},
    "MirrorHighWater": {"id"},
    "MirrorItem": {"id", "number"},
    "MirrorClosedBy": {"id"},
}
# The query shape each operation must have, as GitHub would accept and the fake answers
# it: argument -> the variable bound to it, and every other name the text uses (fields,
# arguments, types, enum values). A misspelt or extra name, a variable bound to another
# argument or a dropped filter fails loudly, as the hosted API would reject or change it.
ISSUE_SELECTION = "__typename id number url state author login body"
QUERY_SHAPES: dict[str, tuple[dict[str, str], str]] = {
    "MirrorIssues": (
        {"id": "id", "first": "first", "after": "after", "createdBy": "creator"},
        "ID String Int node id Repository issues first after filterBy createdBy states"
        " OPEN CLOSED orderBy field CREATED_AT direction ASC nodes pageInfo hasNextPage"
        " endCursor " + ISSUE_SELECTION,
    ),
    "MirrorLabel": (
        {"id": "id", "name": "name"},
        "ID String node id Repository label name",
    ),
    "MirrorIssue": (
        {"id": "id", "number": "number"},
        "ID Int node id Repository issueOrPullRequest number Issue PullRequest "
        + ISSUE_SELECTION,
    ),
    "MirrorIssueNode": (
        {"id": "id"},
        "ID node id Issue title updatedAt repository labels first nodes name "
        + ISSUE_SELECTION,
    ),
    "MirrorUpdated": (
        {
            "id": "id",
            "first": "first",
            "after": "after",
            "createdBy": "creator",
            "since": "since",
        },
        (
            "ID String Int DateTime node id Repository issues first after filterBy"
            " createdBy since states OPEN CLOSED nodes number pageInfo hasNextPage"
            " endCursor"
        ),
    ),
    "MirrorComments": (
        {"id": "id", "first": "first", "after": "after"},
        (
            "ID String Int node id Issue comments first after nodes author login body"
            " pageInfo hasNextPage endCursor"
        ),
    ),
    "MirrorInboundIssues": (
        {"id": "id", "first": "first", "after": "after", "since": "since"},
        (
            "ID DateTime Int String node id Repository issues first after filterBy since"
            " states OPEN CLOSED orderBy field CREATED_AT direction ASC nodes __typename"
            " number state closedAt updatedAt author login pageInfo hasNextPage endCursor"
        ),
    ),
    "MirrorInboundPulls": (
        {"id": "id", "first": "first", "after": "after"},
        (
            "ID Int String node id Repository pullRequests first after states OPEN CLOSED"
            " MERGED orderBy field UPDATED_AT direction DESC nodes __typename number state"
            " merged mergedAt updatedAt body author login mergedBy mergeCommit oid"
            " pageInfo hasNextPage endCursor"
        ),
    ),
    "MirrorHighWater": (
        {"id": "id"},
        "ID node id Repository issues last nodes number pullRequests",
    ),
    "MirrorItem": (
        {"id": "id", "number": "number"},
        (
            "ID Int node id Repository issueOrPullRequest number Issue __typename state"
            " closedAt updatedAt author login PullRequest merged mergedAt body mergedBy"
            " mergeCommit oid"
        ),
    ),
    "MirrorClosedBy": (
        {"id": "id"},
        (
            "ID node id Issue timelineItems itemTypes CLOSED_EVENT last nodes ClosedEvent"
            " createdAt closer __typename PullRequest number url merged mergedBy login"
            " mergeCommit oid Commit"
        ),
    ),
}
BINDING_RE = re.compile(r"(?<![$\w])(\w+)\s*:\s*\$(\w+)")
NAME_RE = re.compile(r"(?<![$\w])[A-Za-z_]\w*")
# Mutation -> (its input type, the input fields it takes, the names its selection may use).
MUTATION_SHAPES: dict[str, tuple[str, set[str], set[str]]] = {
    "createIssue": (
        "CreateIssueInput",
        {"repositoryId", "title", "body", "labelIds"},
        {"issue", "title", *ISSUE_SELECTION.split()},
    ),
    "createLabel": (
        "CreateLabelInput",
        {"repositoryId", "name", "color"},
        {"label", "id", "name", "clientMutationId"},
    ),
    "updateIssue": ("UpdateIssueInput", {"id", "title", "body"}, {"issue", "id"}),
    "closeIssue": ("CloseIssueInput", {"issueId"}, {"issue", "id"}),
    "reopenIssue": ("ReopenIssueInput", {"issueId"}, {"issue", "id"}),
    "addComment": ("AddCommentInput", {"subjectId", "body"}, {"clientMutationId"}),
    "addLabelsToLabelable": (
        "AddLabelsToLabelableInput",
        {"labelableId", "labelIds"},
        {"clientMutationId"},
    ),
    "removeLabelsFromLabelable": (
        "RemoveLabelsFromLabelableInput",
        {"labelableId", "labelIds"},
        {"clientMutationId"},
    ),
}
MUTATION_HEAD_RE = re.compile(
    r"^\s*mutation\s*\(\s*\$input\s*:\s*(\w+)!\s*\)\s*\{\s*(\w+)\(input:\s*\$input\)"
    r"\s*\{(.*)\}\s*\}\s*$",
    re.DOTALL,
)


def check_query(name: str, query: str) -> None:
    """Fail loudly unless ``query`` has the shape the table records for ``name``."""
    bindings, names = QUERY_SHAPES[name]
    found = dict(BINDING_RE.findall(query))
    if found != bindings or len(BINDING_RE.findall(query)) != len(found):
        raise Unrecognised(f"{name}: arguments bound {found}, expected {bindings}")
    used = set(NAME_RE.findall(query)) - {"query", "on", name}
    if used != set(names.split()):
        odd = sorted(used ^ set(names.split()))
        raise Unrecognised(f"{name}: names not in the recorded shape: {odd}")


def check_mutation(name: str, query: str, fields: Any) -> None:
    """Fail loudly unless the mutation names its input type, takes only the input
    fields the type has, and selects only fields its payload has."""
    head = MUTATION_HEAD_RE.match(query)
    input_type, inputs, selection = MUTATION_SHAPES[name]
    if head is None or head.group(1) != input_type or head.group(2) != name:
        raise Unrecognised(f"{name}: not `mutation($input: {input_type}!)`")
    extra = sorted(set(fields) - inputs) if isinstance(fields, dict) else ["(input)"]
    if extra:
        raise Unrecognised(f"{name}: input fields {inputs} has no {extra}")
    odd = sorted(set(NAME_RE.findall(head.group(3))) - selection)
    if odd:
        raise Unrecognised(f"{name}: selects what its payload lacks: {odd}")


ISSUE_WRITES = {
    "updateIssue": "id",
    "closeIssue": "issueId",
    "reopenIssue": "issueId",
    "addComment": "subjectId",
    "addLabelsToLabelable": "labelableId",
    "removeLabelsFromLabelable": "labelableId",
}
MUTATIONS = {"createIssue", "createLabel"} | set(ISSUE_WRITES)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def fixture(name: str) -> Any:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return strip_notes(data)


def strip_notes(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: strip_notes(v)
            for k, v in data.items()
            if not k.startswith("_") or k.startswith("__")
        }
    if isinstance(data, list):
        return [strip_notes(v) for v in data]
    return data


def fill(data: Any, values: dict[str, Any]) -> Any:
    if isinstance(data, dict):
        return {k: fill(v, values) for k, v in data.items()}
    if isinstance(data, list):
        return [fill(v, values) for v in data]
    if isinstance(data, str):
        if data.startswith("$") and data[1:] in values:
            return values[data[1:]]
        return re.sub(
            r"\$(\w+)", lambda m: str(values.get(m.group(1), m.group(0))), data
        )
    return data


class Unrecognised(Exception):
    pass


class Reply(Exception):
    def __init__(self, code: int, stdout: str = "", stderr: str = "") -> None:
        super().__init__(stderr)
        self.code, self.stdout, self.stderr = code, stdout, stderr


def parse(argv: list[str]) -> tuple[dict[str, str], set[str], list[str]]:
    if not argv or argv[0] != "api":
        raise Unrecognised("only `gh api` is served")
    opts: dict[str, str] = {}
    bools: set[str] = set()
    positional: list[str] = []
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in KNOWN_FLAGS_WITH_VALUE and i + 1 < len(argv):
            opts[arg] = argv[i + 1]
            i += 2
        elif arg in KNOWN_BOOL_FLAGS:
            bools.add(arg)
            i += 1
        elif arg.startswith("-"):
            raise Unrecognised(f"flag not served: {arg}")
        else:
            positional.append(arg)
            i += 1
    if len(positional) != 1:
        raise Unrecognised(f"expected one endpoint, got {positional!r}")
    return opts, bools, positional


def error_reply(name: str, state: dict[str, Any], include: bool) -> Reply:
    err = fill(
        fixture("errors.json")[name],
        {"host": state["host"], "reset": str(int(time.time()) + 3600)},
    )
    stdout = ""
    if include and "status" in err:
        head = [err["status"]] + [
            f"{k}: {v}" for k, v in err.get("headers", {}).items()
        ]
        stdout = "\r\n".join(head) + "\r\n\r\n" + json.dumps(err.get("body", {}))
    elif "body" in err:
        stdout = json.dumps(err["body"])
    return Reply(err["exit"], stdout, err["stderr"])


def graphql_error(message: str, kind: str = "NOT_FOUND") -> Reply:
    body = {"data": None, "errors": [{"type": kind, "message": message}]}
    return Reply(1, json.dumps(body), f"gh: {message}\n")


def find_repo(state: dict[str, Any], owner: str, name: str) -> dict[str, Any] | None:
    repos: list[dict[str, Any]] = state["repos"]
    for repo in repos:
        if (
            repo["owner"].lower() == owner.lower()
            and repo["name"].lower() == name.lower()
        ):
            return repo
    return None


def repo_by_node(state: dict[str, Any], node_id: str) -> dict[str, Any]:
    repo: dict[str, Any] | None = next(
        (r for r in state["repos"] if r["node_id"] == node_id), None
    )
    if repo is None:
        raise graphql_error(
            f"Could not resolve to a node with the global id of '{node_id}'"
        )
    return repo


def url_of(state: dict[str, Any], repo: dict[str, Any], kind: str, number: int) -> str:
    return f"https://{state['host']}/{repo['owner']}/{repo['name']}/{kind}/{number}"


def issue_node(
    state: dict[str, Any], repo: dict[str, Any], issue: dict[str, Any]
) -> Any:
    return fill(
        fixture("graphql_issue_node.json"),
        {
            "issue_node_id": issue["node_id"],
            "issue_number": issue["number"],
            "issue_url": url_of(state, repo, "issues", issue["number"]),
            "issue_state": issue["state"],
            "issue_title": issue["title"],
            "issue_body": issue["body"],
            "author": issue["author"],
            "repo_node_id": repo["node_id"],
            "updated_at": issue.get("updated_at", "1970-01-01T00:00:00Z"),
            "labels": [{"id": label_id(repo, n), "name": n} for n in issue["labels"]],
        },
    )


def label_id(repo: dict[str, Any], name: str) -> str:
    """A label's node ID; a label seeded only on an issue gets one in the repository."""
    labels = repo.setdefault("labels", [])
    for lb in labels:
        if lb["name"].lower() == name.lower():
            return str(lb["id"])
    label = {"id": f"LA_kwDOfake{len(labels) + 1}", "name": name}
    labels.append(label)
    return label["id"]


def serve(
    state: dict[str, Any], argv: list[str], stdin: str, record: dict[str, Any]
) -> str:
    opts, bools, (endpoint,) = parse(argv)
    host = opts.get("--hostname")
    if host != state["host"]:
        raise Unrecognised(f"--hostname must name {state['host']}, got {host!r}")
    include = bool(bools & {"-i", "--include"})
    faults = state.get("faults", {})
    body: dict[str, Any] = {}
    if endpoint == "user" and "--input" not in opts:
        record["route"] = "GET user"
    elif re.fullmatch(r"repos/[^/?]+/[^/?]+", endpoint) and "--input" not in opts:
        record["route"] = "GET repos/OWNER/NAME"
    elif (
        re.fullmatch(r"repos/[^/?]+/[^/?]+/pulls/[0-9]+", endpoint)
        and "--input" not in opts
    ):
        record["route"] = "GET repos/OWNER/NAME/pulls/N"
    elif endpoint == "graphql" and opts.get("--input") == "-":
        body = json.loads(stdin)
        query = body.get("query", "")
        variables = body.get("variables") or {}
        mutation, named = MUTATION_RE.match(query), QUERY_RE.match(query)
        if mutation and mutation.group(1) in MUTATIONS:
            check_mutation(mutation.group(1), query, variables.get("input"))
            record["route"] = f"graphql {mutation.group(1)}"
        elif named and named.group(1) in QUERIES:
            missing = QUERIES[named.group(1)] - set(variables)
            if missing:
                raise Unrecognised(f"{named.group(1)} without {sorted(missing)}")
            check_query(named.group(1), query)
            record["route"] = f"graphql {named.group(1)}"
        else:
            raise Unrecognised(f"graphql operation not served: {query!r}")
    else:
        raise Unrecognised(f"route not served: {endpoint}")

    if faults.get("offline"):
        record["fault"] = "offline"
        raise error_reply("offline", state, include)
    if faults.get("unauthenticated"):
        record["fault"] = "unauthenticated"
        raise error_reply("unauthenticated", state, include)
    if faults.get("rate_limited"):
        record["fault"] = "rate_limited"
        raise error_reply(f"rate_limited_{faults['rate_limited']}", state, include)

    route = record["route"]
    failing = (faults.get("fail_query") or {}).get(route.split()[-1])
    if failing and route.startswith("graphql Mirror"):
        record["fault"] = "fail_query"
        raise error_reply(str(failing), state, include)
    if route == "GET user":
        return json.dumps(
            fill(
                fixture("rest_user.json"),
                {
                    "login": state["login"],
                    "user_html_url": f"https://{state['host']}/{state['login']}",
                },
            )
        )
    if route == "GET repos/OWNER/NAME":
        return get_repo(state, endpoint, faults, include, record)
    if route == "GET repos/OWNER/NAME/pulls/N":
        return get_pull(state, endpoint, faults, include)
    variables = body.get("variables") or {}
    if route == "graphql MirrorIssues":
        return list_issues(state, body.get("query", ""), variables, faults, record)
    if route == "graphql MirrorLabel":
        repo = repo_by_node(state, variables["id"])
        record["repo_node_id"] = repo["node_id"]
        label = next(
            (
                lb
                for lb in repo.setdefault("labels", [])
                if lb["name"].lower() == str(variables["name"]).lower()
            ),
            None,
        )
        reply = fill(fixture("graphql_label.json"), {"label": label})
        return json.dumps(reply)
    if route == "graphql MirrorIssue":
        return get_issue(state, variables, record)
    if route == "graphql MirrorIssueNode":
        return get_issue_node(state, variables, faults, record)
    if route == "graphql MirrorUpdated":
        return list_updated(state, variables, record)
    if route == "graphql MirrorComments":
        return list_comments(state, variables, faults, record)
    if route == "graphql MirrorInboundIssues":
        return list_inbound_issues(state, variables, faults, record)
    if route == "graphql MirrorInboundPulls":
        return list_inbound_pulls(state, variables, faults, record)
    if route == "graphql MirrorHighWater":
        return high_water(state, variables, faults, record)
    if route == "graphql MirrorItem":
        return get_item(state, variables, faults, record)
    if route == "graphql MirrorClosedBy":
        return closed_by(state, variables, faults, record)
    fields = variables.get("input", {})
    if route == "graphql createLabel":
        return create_label(state, fields, record)
    if route == "graphql createIssue":
        return create_issue(state, fields, faults, record)
    return write_issue(state, route.split()[1], fields, faults, record)


def get_pull(
    state: dict[str, Any], endpoint: str, faults: dict[str, Any], include: bool
) -> str:
    _, owner, name, _, number = endpoint.split("/")
    repo = find_repo(state, owner, name)
    pull = next(
        (p for p in (repo or {}).get("pulls", []) if p["number"] == int(number)),
        None,
    )
    if repo is None or pull is None:
        raise error_reply("not_found", state, include)
    malformed = faults.get("malformed_pull")
    if malformed == "not_json":
        return "<html>unexpected</html>"
    reply = fill(
        fixture("rest_pull.json"),
        {
            "pull_node_id": pull["node_id"],
            "pull_number": pull["number"],
            "pull_url": url_of(state, repo, "pull", pull["number"]),
            "pull_body": pull.get("body"),
            "author": pull.get("author", "contributor"),
        },
    )
    if malformed == "no_user":
        reply.pop("user", None)
    if malformed == "no_body":
        reply.pop("body", None)
    return json.dumps(reply)


def get_repo(
    state: dict[str, Any],
    endpoint: str,
    faults: dict[str, Any],
    include: bool,
    record: dict[str, Any],
) -> str:
    _, owner, name = endpoint.split("/")
    repo = find_repo(state, owner, name)
    if repo is None:
        raise error_reply("not_found", state, include)
    record["repo_node_id"] = repo["node_id"]
    reply = fill(
        fixture("rest_repo.json"),
        {
            "repo_node_id": repo["node_id"],
            "repo_name": repo["name"],
            "repo_owner": repo["owner"],
            "repo_full_name": f"{repo['owner']}/{repo['name']}",
            "repo_html_url": f"https://{state['host']}/{repo['owner']}/{repo['name']}",
        },
    )
    rename = faults.get("rename_after_check")
    if rename and rename["repo_node_id"] == repo["node_id"] and not rename.get("done"):
        old_name = repo["name"]
        repo["name"] = rename["new_name"]
        state["repos"].append(
            {
                "node_id": rename["squatter_node_id"],
                "owner": repo["owner"],
                "name": old_name,
                "labels": [],
                "issues": [],
                "pulls": [],
            }
        )
        rename["done"] = True
    return json.dumps(reply)


STATES_RE = re.compile(r"\bstates:\s*\[([A-Z_,\s]*)\]")


def listed_states(query: str) -> set[str]:
    """The issue states a listing asks for; GitHub returns every state when it names none."""
    m = STATES_RE.search(query)
    if m is None:
        return {"OPEN", "CLOSED"}
    return {s for s in re.split(r"[\s,]+", m.group(1)) if s}


def list_issues(
    state: dict[str, Any],
    query: str,
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    repo = repo_by_node(state, variables["id"])
    record["repo_node_id"] = repo["node_id"]
    size = min(int(variables["first"]), int(faults.get("page_size", 100)), 100)
    after = variables.get("after")
    start = int(after.split(":")[1]) if after else 0
    page = start // size + 1
    record["page"] = page
    if faults.get("failed_page") == page:
        record["fault"] = "failed_page"
        raise error_reply("bad_gateway", state, False)
    states = listed_states(query)
    visible = [
        i
        for i in repo["issues"]
        if (faults.get("ignore_creator_filter") or i["author"] == variables["creator"])
        and i["state"] in states
        and not i.get("hidden_for")
    ]
    chunk = visible[start : start + size]
    more = start + size < len(visible)
    malformed = faults.get("malformed_page") or {}
    if not more:  # a complete listing: lagging issues come one listing closer
        for issue in repo["issues"]:
            if issue.get("hidden_for"):
                issue["hidden_for"] -= 1
    reply = fill(
        fixture("graphql_issues_page.json"),
        {
            "nodes": [issue_node(state, repo, i) for i in chunk],
            "has_next": more,
            "end_cursor": f"cursor:{start + len(chunk)}" if chunk else None,
        },
    )
    if malformed.get("page") == page:
        record["fault"] = "malformed_page"
        info = reply["data"]["node"]["issues"]["pageInfo"]
        if malformed.get("kind") == "stuck_cursor":
            info.update(hasNextPage=True, endCursor=f"cursor:{start}")
        else:
            info.pop("hasNextPage", None)
    return json.dumps(reply)


def get_issue(
    state: dict[str, Any], variables: dict[str, Any], record: dict[str, Any]
) -> str:
    repo = repo_by_node(state, variables["id"])
    record["repo_node_id"] = repo["node_id"]
    number = int(variables["number"])
    issue = next((i for i in repo["issues"] if i["number"] == number), None)
    pull = next(
        (p for p in repo.setdefault("pulls", []) if p["number"] == number), None
    )
    if issue is not None:
        node = issue_node(state, repo, issue)
    elif pull is not None:
        node = fill(
            fixture("graphql_pull_node.json"),
            {
                "pull_node_id": pull["node_id"],
                "pull_number": number,
                "pull_url": url_of(state, repo, "pull", number),
            },
        )
    else:
        raise graphql_error(
            f"Could not resolve to an issue or pull request with the number of {number}."
        )
    return json.dumps(fill(fixture("graphql_issue.json"), {"node": node}))


def issue_by_node(
    state: dict[str, Any], node_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    for repo in state["repos"]:
        for issue in repo["issues"]:
            if issue["node_id"] == node_id:
                return repo, issue
    raise graphql_error(
        f"Could not resolve to a node with the global id of '{node_id}'"
    )


def get_issue_node(
    state: dict[str, Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    repo, issue = issue_by_node(state, str(variables["id"]))
    record["repo_node_id"] = repo["node_id"]
    if faults.pop("_readback_armed", False):  # the read-back after a write fails, once
        kind = faults.pop("interrupt_readback", None)
        record["fault"] = "interrupt_readback"
        raise error_reply(
            kind if isinstance(kind, str) else "bad_gateway", state, False
        )
    reply = fill(fixture("graphql_node.json"), {"node": issue_node(state, repo, issue)})
    return json.dumps(reply)


def list_updated(
    state: dict[str, Any], variables: dict[str, Any], record: dict[str, Any]
) -> str:
    """The creator's issues updated at or after ``since`` (all on one page here)."""
    repo = repo_by_node(state, variables["id"])
    record["repo_node_id"] = repo["node_id"]
    since = str(variables["since"])
    nodes = [
        {"id": i["node_id"], "number": i["number"]}
        for i in repo["issues"]
        if i["author"] == variables["creator"]
        and i.get("updated_at", "1970-01-01T00:00:00Z") >= since
    ]
    reply = fill(
        fixture("graphql_issues_page.json"),
        {"nodes": nodes, "has_next": False, "end_cursor": None},
    )
    return json.dumps(reply)


def list_comments(
    state: dict[str, Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    repo, issue = issue_by_node(state, str(variables["id"]))
    record["repo_node_id"] = repo["node_id"]
    size = min(int(variables["first"]), int(faults.get("comments_page_size", 100)))
    after = variables.get("after")
    start = int(after.split(":")[1]) if after else 0
    page = start // size + 1
    if faults.get("failed_comments_page") == page:
        record["fault"] = "failed_comments_page"
        raise error_reply("bad_gateway", state, False)
    comments = issue.setdefault("comments", [])
    chunk = comments[start : start + size]
    reply = fill(
        fixture("graphql_comments_page.json"),
        {
            "nodes": [
                {"author": {"login": c["author"]}, "body": c["body"]} for c in chunk
            ],
            "has_next": start + size < len(comments),
            "end_cursor": f"cursor:{start + len(chunk)}" if chunk else None,
        },
    )
    if faults.get("malformed_comments_page") == page:
        record["fault"] = "malformed_comments_page"
        reply["data"]["node"]["comments"]["pageInfo"].pop("hasNextPage", None)
    return json.dumps(reply)


EPOCH = "1970-01-01T00:00:00Z"


def inbound_issue(
    repo: dict[str, Any], issue: dict[str, Any], faults: dict[str, Any]
) -> Any:
    node = fill(
        fixture("graphql_inbound_issue.json"),
        {
            "issue_node_id": issue["node_id"],
            "issue_number": issue["number"],
            "issue_state": issue["state"],
            "closed_at": issue.get("closed_at") if issue["state"] == "CLOSED" else None,
            "updated_at": issue.get("updated_at", EPOCH),
            "author": issue["author"],
        },
    )
    if faults.get("instruction_titles"):  # served although no title was asked for
        node["title"] = faults["instruction_titles"]
    return node


def merge_fields(pull: dict[str, Any]) -> dict[str, Any]:
    merged = pull.get("state") == "MERGED"
    return {
        "merged": merged,
        "mergedBy": {"login": pull.get("merged_by")} if merged else None,
        "mergeCommit": {"oid": pull.get("merge_commit")} if merged else None,
    }


def inbound_pull(pull: dict[str, Any], faults: dict[str, Any]) -> Any:
    body = pull.get("body")
    text = faults.get("instruction_titles")
    if text and isinstance(body, str):
        body = body + "\n\n" + text
    merge = merge_fields(pull)
    node = fill(
        fixture("graphql_inbound_pull.json"),
        {
            "pull_node_id": pull["node_id"],
            "pull_number": pull["number"],
            "pull_state": pull.get("state", "OPEN"),
            "merged": merge["merged"],
            "merged_at": pull.get("merged_at"),
            "updated_at": pull.get("updated_at", EPOCH),
            "pull_body": body,
            "author": pull.get("author", "contributor"),
            "merged_by": merge["mergedBy"],
            "merge_commit": merge["mergeCommit"],
        },
    )
    if text:
        node["title"] = text
    return node


def page_of(
    items: list[Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
    operation: str,
) -> tuple[list[Any], bool, str | None]:
    """One page of ``items`` by the ``cursor:N`` convention; ``failed_inbound_page``
    ({"op", "page"}) fails that page of that listing with HTTP 502."""
    size = min(int(variables["first"]), int(faults.get("page_size", 100)), 100)
    after = variables.get("after")
    start = int(after.split(":")[1]) if after else 0
    page = start // size + 1
    record["page"] = page
    failing = faults.get("failed_inbound_page") or {}
    if failing.get("op") == operation and failing.get("page") == page:
        record["fault"] = "failed_inbound_page"
        raise Reply(
            1, json.dumps({"message": "Server Error"}), "gh: HTTP 502: Bad Gateway\n"
        )
    chunk = items[start : start + size]
    end = f"cursor:{start + len(chunk)}" if chunk else None
    return chunk, start + size < len(items), end


def list_inbound_issues(
    state: dict[str, Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    """Every author's issues updated at or after ``since``, oldest number first."""
    repo = repo_by_node(state, variables["id"])
    record["repo_node_id"] = repo["node_id"]
    since = str(variables["since"])
    visible = sorted(
        (i for i in repo["issues"] if i.get("updated_at", EPOCH) >= since),
        key=lambda i: i["number"],
    )
    chunk, more, end = page_of(
        visible, variables, faults, record, "MirrorInboundIssues"
    )
    reply = fill(
        fixture("graphql_issues_page.json"),
        {
            "nodes": [inbound_issue(repo, i, faults) for i in chunk],
            "has_next": more,
            "end_cursor": end,
        },
    )
    return json.dumps(reply)


def list_inbound_pulls(
    state: dict[str, Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    """Every pull request, most recently updated first."""
    repo = repo_by_node(state, variables["id"])
    record["repo_node_id"] = repo["node_id"]
    pulls = sorted(
        repo.setdefault("pulls", []),
        key=lambda p: (p.get("updated_at", EPOCH), p["number"]),
        reverse=True,
    )
    chunk, more, end = page_of(pulls, variables, faults, record, "MirrorInboundPulls")
    reply = fill(
        fixture("graphql_pulls_page.json"),
        {
            "nodes": [inbound_pull(p, faults) for p in chunk],
            "has_next": more,
            "end_cursor": end,
        },
    )
    return json.dumps(reply)


def high_water(
    state: dict[str, Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    """The newest issue and pull request; ``open_after_high_water`` (a login): that
    author opens an issue right after this answer, as if during the full pass."""
    repo = repo_by_node(state, variables["id"])
    record["repo_node_id"] = repo["node_id"]

    def newest(items: list[dict[str, Any]]) -> list[dict[str, int]]:
        return [{"number": max(i["number"] for i in items)}] if items else []

    reply = fill(
        fixture("graphql_high_water.json"),
        {
            "issue_nodes": newest(repo["issues"]),
            "pull_nodes": newest(repo.setdefault("pulls", [])),
        },
    )
    author = faults.get("open_after_high_water")
    if author:
        taken = [i["number"] for i in repo["issues"]] + [
            p["number"] for p in repo["pulls"]
        ]
        number = max(taken, default=0) + 1
        repo["issues"].append(
            {
                "node_id": f"I_kwDOlate{number}",
                "number": number,
                "author": author,
                "title": "late",
                "body": "late",
                "labels": [],
                "state": "OPEN",
                "comments": [],
                "closing_events": [],
                "updated_at": now_iso(),
            }
        )
    return json.dumps(reply)


def get_item(
    state: dict[str, Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    repo = repo_by_node(state, variables["id"])
    record["repo_node_id"] = repo["node_id"]
    number = int(variables["number"])
    if not -(2**31) <= number < 2**31:
        # GraphQL's Int is 32-bit: GitHub refuses the variable itself (provisional).
        raise graphql_error(
            "Variable $number of type Int! was provided invalid value", "INVALID_VALUE"
        )
    issue = next((i for i in repo["issues"] if i["number"] == number), None)
    pull = next(
        (p for p in repo.setdefault("pulls", []) if p["number"] == number), None
    )
    if issue is not None:
        node = inbound_issue(repo, issue, faults)
    elif pull is not None:
        node = inbound_pull(pull, faults)
    else:
        raise graphql_error(
            f"Could not resolve to an issue or pull request with the number of {number}."
        )
    return json.dumps(fill(fixture("graphql_issue.json"), {"node": node}))


def closed_by(
    state: dict[str, Any],
    variables: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    """The issue's latest closing event; ``failed_timeline`` (issue numbers) fails it."""
    repo, issue = issue_by_node(state, str(variables["id"]))
    record["repo_node_id"] = repo["node_id"]
    if issue["number"] in (faults.get("failed_timeline") or []):
        record["fault"] = "failed_timeline"
        raise error_reply("bad_gateway", state, False)
    events = issue.get("closing_events") or []
    nodes: list[dict[str, Any]] = []
    if events:
        last = events[-1]
        closer = last.get("closer")
        node: Any = None
        if closer and "pull" in closer:
            # ``repo``: a pull request in another of the fake's repositories (by name).
            home = repo
            if closer.get("repo"):
                owner, name = str(closer["repo"]).split("/")
                home = find_repo(state, owner, name) or repo
            pull = next(p for p in home["pulls"] if p["number"] == closer["pull"])
            node = {
                "__typename": "PullRequest",
                "number": pull["number"],
                "url": url_of(state, home, "pull", pull["number"]),
            }
            node.update(merge_fields(pull))
        elif closer and "commit" in closer:
            node = {"__typename": "Commit", "oid": closer["commit"]}
        nodes = [{"createdAt": last["at"], "closer": node}]
    reply = fill(fixture("graphql_closed_by.json"), {"events": nodes})
    return json.dumps(reply)


def stored_body(body: str, faults: dict[str, Any]) -> str:
    """The body as GitHub stores it; ``stores_body_as`` [old, new] alters it."""
    alter = faults.get("stores_body_as")
    return body.replace(alter[0], alter[1]) if alter else body


def write_issue(
    state: dict[str, Any],
    mutation: str,
    fields: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    repo, issue = issue_by_node(state, str(fields.get(ISSUE_WRITES[mutation], "")))
    record["repo_node_id"] = repo["node_id"]
    record["write"] = mutation
    record["subject"] = issue["number"]
    if "labelIds" in fields:
        record["label_ids"] = len(fields["labelIds"])
    failing = (faults.get("fail_write") or {}).get(mutation)
    if failing:
        record["fault"] = "fail_write"
        raise error_reply(str(failing), state, False)
    if mutation in (faults.get("drop_write") or []):
        record["fault"] = "drop_write"  # GitHub answers success but keeps nothing
    elif mutation == "updateIssue":
        if "title" in fields:
            issue["title"] = str(fields["title"])
        if "body" in fields:
            issue["body"] = stored_body(str(fields["body"]), faults)
    elif mutation == "closeIssue":
        issue["state"], issue["closed_at"] = "CLOSED", now_iso()
        issue.setdefault("closing_events", []).append({"at": now_iso(), "closer": None})
    elif mutation == "reopenIssue":
        issue["state"], issue["closed_at"] = "OPEN", None
    elif mutation == "addComment":
        issue.setdefault("comments", []).append(
            {"author": state["login"], "body": str(fields.get("body", ""))}
        )
    else:
        by_id = {lb["id"]: lb["name"] for lb in repo.setdefault("labels", [])}
        unknown = [i for i in fields.get("labelIds", []) if i not in by_id]
        if unknown:
            raise graphql_error(
                f"Could not resolve to a node with the global id of '{unknown[0]}'"
            )
        names = [by_id[i] for i in fields.get("labelIds", [])]
        have = {n.lower() for n in issue["labels"]}
        gone = {n.lower() for n in names}  # label names are unique without case
        if mutation == "addLabelsToLabelable":
            issue["labels"] += [n for n in names if n.lower() not in have]
        else:
            issue["labels"] = [n for n in issue["labels"] if n.lower() not in gone]
    if record.get("fault") != "drop_write":
        issue["updated_at"] = now_iso()
    later = (faults.get("collaborator_after_write") or {}).pop(mutation, None)
    if later:  # a collaborator changes the issue before the mirror reads it back
        issue.update(later)
        issue["updated_at"] = now_iso()
    if faults.get("interrupt_readback"):
        faults["_readback_armed"] = True
    name = (
        "graphql_addComment.json" if mutation == "addComment" else "graphql_write.json"
    )
    reply = fill(
        fixture(name),
        {
            "mutation": mutation,
            "node_id": issue["node_id"],
            "issue_number": issue["number"],
        },
    )
    return json.dumps({"data": {mutation: reply["data"]["$mutation"]}})


def create_label(
    state: dict[str, Any], fields: dict[str, Any], record: dict[str, Any]
) -> str:
    repo = repo_by_node(state, fields.get("repositoryId", ""))
    labels = repo.setdefault("labels", [])
    name = str(fields.get("name", ""))
    refuse = state.get("faults", {}).get("refuse_label")
    if refuse and refuse in name:
        raise graphql_error("Name is too long", "UNPROCESSABLE")
    if not name or any(lb["name"].lower() == name.lower() for lb in labels):
        raise graphql_error("Name has already been taken", "UNPROCESSABLE")
    label = {"id": f"LA_kwDOfake{len(labels) + 1}", "name": name}
    labels.append(label)
    record["repo_node_id"] = repo["node_id"]
    record["write"] = "createLabel"
    return json.dumps(fill(fixture("graphql_createLabel.json"), {"label": label}))


def create_issue(
    state: dict[str, Any],
    fields: dict[str, Any],
    faults: dict[str, Any],
    record: dict[str, Any],
) -> str:
    if faults.get("fail_create"):
        record["fault"] = "fail_create"
        raise error_reply(str(faults["fail_create"]), state, False)
    repo = repo_by_node(state, fields.get("repositoryId", ""))
    by_id = {lb["id"]: lb["name"] for lb in repo.setdefault("labels", [])}
    unknown = [i for i in fields.get("labelIds", []) if i not in by_id]
    if unknown:
        raise graphql_error(
            f"Could not resolve to a node with the global id of '{unknown[0]}'"
        )
    title = str(fields.get("title", ""))
    if len(title) > 256:
        raise graphql_error(
            "title is too long (maximum is 256 characters)", "UNPROCESSABLE"
        )
    if faults.get("refuse_create_titled") and faults["refuse_create_titled"] in title:
        raise graphql_error("Title is invalid", "UNPROCESSABLE")
    numbers = [i["number"] for i in repo["issues"]] + [
        p["number"] for p in repo.setdefault("pulls", [])
    ]
    number = max(numbers, default=0) + 1
    issue = {
        "node_id": "I_kwDOfake" + re.sub(r"\W", "", repo["node_id"]) + str(number),
        "number": number,
        "author": state["login"],
        "title": fields.get("title", ""),
        "body": fields.get("body", ""),
        "labels": [by_id[i] for i in fields.get("labelIds", [])],
        "state": "CLOSED" if faults.get("close_created") else "OPEN",
        "comments": [],
        "closing_events": [],
        "hidden_for": int(faults.get("listing_lag", 0)),
        "updated_at": now_iso(),
    }
    issue["body"] = stored_body(str(issue["body"]), faults)
    repo["issues"].append(issue)
    record["repo_node_id"] = repo["node_id"]
    record["write"] = "createIssue"
    if faults.get("hang_after_create"):
        record["hang"] = float(faults["hang_after_create"])
    if faults.get("lose_create_response"):
        record["fault"] = "lose_create_response"
        raise error_reply("lost_response", state, False)
    if faults.get("error_after_create"):
        record["fault"] = "error_after_create"
        named = faults["error_after_create"]
        raise error_reply(
            named if isinstance(named, str) else "error_after_write", state, False
        )
    return json.dumps(
        fill(
            fixture("graphql_createIssue.json"),
            {"issue": issue_node(state, repo, issue)},
        )
    )


def main(argv: list[str]) -> int:
    state_path = Path(os.environ["FAKE_GH_STATE"])
    stdin = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
    with open(state_path, encoding="utf-8") as fh:
        delay = json.load(fh).get("faults", {}).get("delay", 0)
    if delay:
        time.sleep(float(delay))
    with open(str(state_path) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        record: dict[str, Any] = {
            "argv": argv,
            "ambient": sorted(k for k in ("GH_REPO", "GH_HOST") if k in os.environ),
            "fault": None,
            "caller_pid": os.getppid(),
        }
        state["calls"].append(record)
        try:
            out = serve(state, argv, stdin, record)
            code, stderr = 0, ""
        except Unrecognised as exc:
            state["unrecognised"].append({"argv": argv, "reason": str(exc)})
            out, code, stderr = (
                "",
                UNRECOGNISED_EXIT,
                f"fake gh: unrecognised call: {exc}\n",
            )
        except Reply as reply:
            out, code, stderr = reply.stdout, reply.code, reply.stderr
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    if record.get("hang"):
        time.sleep(record["hang"])
    sys.stdout.write(out)
    sys.stderr.write(stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
