"""The ruff-zero run script's offline checks: the open pull request read, suppressions, the
real fix, and the pull request body."""

import difflib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

LOOP = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ruff_zero_checks", LOOP / "checks.py")
checks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checks)


def pr(url, head):
    return {"url": url, "headRefName": head}


def test_open_prs_lists_only_this_loops_branches():
    listing = [
        pr("u1", "loop/ruff-zero/1"),
        pr("u2", "loop/ruff-zero-x/1"),
        pr("u3", "fix"),
    ]
    assert checks.open_loop_prs(listing, "loop/ruff-zero", 100) == ["u1"]


@pytest.mark.parametrize("listing", [None, {"error": 1}, [pr("u", "a")] * 3])
def test_open_prs_refuses_a_read_that_may_be_incomplete(listing):
    assert checks.open_loop_prs(listing, "loop/ruff-zero", 3) is None


def diff(*lines):
    return (
        "--- a/pkg/mod.py\n+++ b/pkg/mod.py\n@@ -1,2 +1,2 @@\n"
        + "\n".join(lines)
        + "\n"
    )


@pytest.mark.parametrize(
    "lines",
    [
        ["+x = dict()  # noqa: C408"],
        ["+x = dict()  # noqa"],
        ["+# ruff: noqa: ISC004"],
        ["+# ruff: disable[ISC004]"],
        ["+x = y  # ruff: ignore[F821]"],
        ["+# ruff: file-ignore[F821]"],
        ["+# RUFF: enable[F821]"],
        ["-y = 1  # noqa: E501, C408", "+y = 1  # noqa: E501"],
        ["-a = 1  # noqa: F821", "+a = 1", "+b = c  # noqa: F821"],
    ],
)
def test_suppressions_refuses_any_added_or_changed_directive_line(lines):
    assert checks.added_suppressions(diff(*lines))


def test_suppressions_allows_a_fix_or_a_removed_directive():
    assert checks.added_suppressions(diff("-x = dict()", "+x = {}")) == []
    assert (
        checks.added_suppressions(diff("-import os  # noqa: F401", "+import os")) == []
    )


def test_suppressions_refuses_a_ruff_configuration_change():
    text = "--- a/pyproject.toml\n+++ b/pyproject.toml\n@@ -1 +1 @@\n-a\n+b\n"
    assert checks.added_suppressions(text)


def test_fixed_needs_the_selected_drop_and_no_rule_rising():
    before = [{"code": "ISC004"}, {"code": "E501"}]
    assert checks.fix_problems(before, [{"code": "E501"}], {"ISC004"}, 1) == []
    assert checks.fix_problems(before, before, {"ISC004"}, 1)
    rose = [{"code": "E501"}, {"code": "F821"}]
    assert checks.fix_problems(before, rose, {"ISC004"}, 1) == ["F821 rose from 0 to 1"]


BEFORE = 'X = ["a" "b", "c"]\nY = 1  # noqa: F821\n'
FIXED = 'X = [("a" "b"), "c"]\nY = 1  # noqa: F821\n'
HIDING = {
    "ruff: ignore": FIXED + "Z = undefined_b  # ruff: ignore[F821]\n",
    "ruff: file-ignore": "# ruff: file-ignore[F821]\n" + FIXED + "Z = undefined_b\n",
    "a moved noqa": 'X = [("a" "b"), "c"]\nY = 1\nZ = undefined_b  # noqa: F821\n',
}


def ruff_ignoring_noqa(tmp_path, source):
    path = tmp_path / "mod.py"
    path.write_text(source)
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--isolated",
            "--select",
            "ISC004,F821,RUF100",
            "--ignore-noqa",
            "--output-format",
            "json",
            "--exit-zero",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)


def staged_diff(before, after):
    lines = difflib.unified_diff(
        before.splitlines(), after.splitlines(), "a/mod.py", "b/mod.py", lineterm=""
    )
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("how", sorted(HIDING))
def test_a_fix_that_hides_a_new_finding_is_refused_both_ways(tmp_path, how):
    after = HIDING[how]
    assert checks.added_suppressions(staged_diff(BEFORE, after))
    problems = checks.fix_problems(
        ruff_ignoring_noqa(tmp_path, BEFORE),
        ruff_ignoring_noqa(tmp_path, after),
        {"ISC004"},
        1,
    )
    assert "F821 rose from 0 to 1" in problems


def test_the_plain_fix_passes_both_ways(tmp_path):
    assert checks.added_suppressions(staged_diff(BEFORE, FIXED)) == []
    before, after = (
        ruff_ignoring_noqa(tmp_path, BEFORE),
        ruff_ignoring_noqa(tmp_path, FIXED),
    )
    assert checks.fix_problems(before, after, {"ISC004"}, 1) == []


# The run script's plain patch of the index, word for word (run.sh, step 10).
PLAIN_STAGED_DIFF = 'git -c color.ui=never -C "$TREE" diff --cached --no-color --no-ext-diff --no-textconv --text'


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def test_a_colour_configured_repository_still_has_its_directive_refused(tmp_path):
    assert PLAIN_STAGED_DIFF + ' > "$RUN/staged.diff"' in (LOOP / "run.sh").read_text()
    git(tmp_path, "init", "-q")
    for key in ("color.ui", "color.diff"):
        git(tmp_path, "config", key, "always")
    (tmp_path / "mod.py").write_text(BEFORE)
    git(tmp_path, "add", "mod.py")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "b")
    (tmp_path / "mod.py").write_text(HIDING["ruff: file-ignore"])
    git(tmp_path, "add", "mod.py")
    coloured = git(tmp_path, "diff", "--cached")
    assert "\x1b[" in coloured  # the fixture really colours its diffs
    plain = git(
        tmp_path,
        "-c",
        "color.ui=never",
        "diff",
        "--cached",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--text",
    )
    assert "\x1b" not in plain
    assert "+# ruff: file-ignore[F821]" in checks.added_suppressions(plain)
    # and a coloured diff handed to the check by mistake is refused, never passed
    assert checks.added_suppressions(coloured)


def test_a_binary_diff_attribute_still_has_its_directive_refused(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / ".gitattributes").write_text("*.py diff=bin\n")
    git(tmp_path, "config", "diff.bin.binary", "true")
    git(tmp_path, "config", "diff.bin.textconv", "cat")
    (tmp_path / "mod.py").write_text(BEFORE)
    git(tmp_path, "add", "mod.py", ".gitattributes")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "b")
    (tmp_path / "mod.py").write_text(HIDING["ruff: file-ignore"])
    git(tmp_path, "add", "mod.py")
    args = ["-c", "color.ui=never", "diff", "--cached", "--no-color", "--no-ext-diff"]
    assert "Binary files" in git(tmp_path, *args, "--no-textconv")  # the hiding case
    plain = git(tmp_path, *args, "--no-textconv", "--text")
    assert "+# ruff: file-ignore[F821]" in checks.added_suppressions(plain)


def remote_urls(tmp_path, fetch, pushes):
    """The fetch and effective push URLs git resolves, read the way run.sh reads them."""
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-q", str(repo))
    git(repo, "remote", "add", "origin", fetch)
    for push in pushes:
        git(repo, "config", "--add", "remote.origin.pushurl", push)
    return (
        git(repo, "remote", "get-url", "origin").strip(),
        git(repo, "remote", "get-url", "--push", "--all", "origin").splitlines(),
    )


def forge_cli(fetch, pushes, issue):
    args = [sys.executable, str(LOOP / "checks.py"), "forge", "--fetch", fetch]
    for push in pushes:
        args += ["--push", push]
    done = subprocess.run(
        args + ["--issue", issue], capture_output=True, text=True, check=False
    )
    return done.returncode, done.stdout + done.stderr


@pytest.mark.parametrize(
    ("push", "named"),
    [
        (
            "https://forge.example.invalid/owner/repo.git",
            "forge.example.invalid/owner/repo",
        ),
        (
            "https://forge.example.invalid:443/owner/repo.git",
            "forge.example.invalid/owner/repo",
        ),
        (
            "ssh://git@forge.example.invalid:22/owner/repo.git",
            "forge.example.invalid/owner/repo",
        ),
    ],
)
def test_forge_reads_an_explicit_default_port_as_the_implicit_one(
    tmp_path, push, named
):
    fetch, pushes = remote_urls(
        tmp_path, "https://forge.example.invalid/owner/repo.git", [push]
    )
    assert pushes == [push]
    issue = "https://forge.example.invalid:443/owner/repo/issues/7"
    assert forge_cli(fetch, pushes, issue) == (0, named + "\n")


@pytest.mark.parametrize(
    ("fetch", "push", "issue"),
    [
        # the critic's case: only the push goes to another service on the same host
        (
            "https://forge.example.invalid/owner/repo.git",
            "https://forge.example.invalid:8443/owner/repo.git",
            "https://forge.example.invalid/owner/repo/issues/7",
        ),
        (
            "https://forge.example.invalid/owner/repo.git",
            "ssh://git@forge.example.invalid:2222/owner/repo.git",
            "https://forge.example.invalid/owner/repo/issues/7",
        ),
        # every URL on the same alternate port: still refused, gh would not address it
        (
            "https://forge.example.invalid:8443/owner/repo.git",
            "https://forge.example.invalid:8443/owner/repo.git",
            "https://forge.example.invalid:8443/owner/repo/issues/7",
        ),
    ],
)
def test_forge_refuses_a_port_other_than_the_default(tmp_path, fetch, push, issue):
    fetch, pushes = remote_urls(tmp_path, fetch, [push])
    rc, out = forge_cli(fetch, pushes, issue)
    assert rc == 1
    assert "a port other than its scheme's default" in out


SECRET = "tok-s3cret"
USER = "loop-user"


@pytest.mark.parametrize(
    ("fetch", "pushes", "issue"),
    [
        # two push destinations
        (
            f"https://{USER}:{SECRET}@forge.example.invalid/owner/repo.git",
            [
                f"https://{USER}:{SECRET}@forge.example.invalid/owner/repo.git",
                f"https://{USER}:{SECRET}@mirror.example.invalid/owner/repo.git",
            ],
            "https://forge.example.invalid/owner/repo/issues/7",
        ),
        # a different repository, an alternate port
        (
            f"https://{USER}:{SECRET}@forge.example.invalid/owner/repo.git",
            [f"https://{USER}:{SECRET}@forge.example.invalid:8443/other/repo.git"],
            "https://forge.example.invalid/owner/repo/issues/7",
        ),
        # a token in a query string
        (
            "https://forge.example.invalid/owner/repo.git",
            [f"https://forge.example.invalid/other/repo.git?access_token={SECRET}"],
            "https://forge.example.invalid/owner/repo/issues/7",
        ),
        # an at-sign in a query or a fragment: a URL parser reads another host
        (
            "https://forge.example.invalid/owner/repo.git",
            [
                f"https://forge.example.invalid?x={SECRET}@other.example.invalid/owner/repo.git"
            ],
            "https://forge.example.invalid/owner/repo/issues/7",
        ),
        (
            "https://forge.example.invalid/owner/repo.git",
            [
                f"https://forge.example.invalid#{SECRET}@other.example.invalid/owner/repo.git"
            ],
            "https://forge.example.invalid/owner/repo/issues/7",
        ),
        # unreadable URLs (a slash in the password; a local path)
        (
            f"https://{USER}:{SECRET}/x@forge.example.invalid/owner/repo.git",
            [f"file:///{USER}:{SECRET}/repo", f"ftp://{USER}:{SECRET}@h/o/r"],
            f"https://{USER}:{SECRET}@forge.example.invalid/owner/repo/issues/7",
        ),
    ],
)
def test_no_forge_error_shows_a_urls_userinfo(tmp_path, fetch, pushes, issue):
    fetch, pushes = remote_urls(tmp_path, fetch, pushes)
    rc, out = forge_cli(fetch, pushes, issue)
    assert rc == 1 and out.strip()
    assert SECRET not in out and USER not in out and "://" not in out


def test_forge_reads_ordinary_userinfo_but_never_a_query_or_fragment():
    issue = "https://forge.example.invalid/owner/repo/issues/7"
    for push in (
        f"https://{USER}:{SECRET}@forge.example.invalid/owner/repo.git",
        f"ssh://{USER}@forge.example.invalid/owner/repo.git",
    ):
        repo, problems = checks.forge_problems(push, [push], issue)
        assert (repo, problems) == ("forge.example.invalid/owner/repo", [])
    for push in (
        "https://forge.example.invalid?x=1@other.example.invalid/owner/repo.git",
        "https://forge.example.invalid#x@other.example.invalid/owner/repo.git",
    ):
        assert checks.repo_identity(push) is None


def test_forge_names_one_repository_with_its_host():
    repo, problems = checks.forge_problems(
        "https://github.com/Owner/Repo.git",
        ["git@github.com:owner/repo.git"],
        "https://github.com/owner/repo/issues/27",
    )
    assert (repo, problems) == ("github.com/owner/repo", [])


@pytest.mark.parametrize(
    ("fetch", "pushes", "issue"),
    [
        # a split fetch and push URL: the push goes elsewhere
        (
            "https://github.com/owner/repo.git",
            ["https://github.com/other/repo.git"],
            "https://github.com/owner/repo/issues/1",
        ),
        # a same-name repository on another host
        (
            "https://git.example.invalid/owner/repo.git",
            ["https://git.example.invalid/owner/repo.git"],
            "https://github.com/owner/repo/issues/1",
        ),
        # two push destinations (a push mirror)
        (
            "https://github.com/owner/repo.git",
            [
                "https://github.com/owner/repo.git",
                "https://mirror.example.invalid/owner/repo.git",
            ],
            None,
        ),
        # two push URLs, even to the same repository
        (
            "https://github.com/owner/repo.git",
            ["https://github.com/owner/repo.git", "git@github.com:owner/repo.git"],
            None,
        ),
        # no push destination, or an unreadable URL
        ("https://github.com/owner/repo.git", [], None),
        ("file:///srv/repo", ["file:///srv/repo"], None),
    ],
)
def test_forge_refuses_anything_but_one_agreed_repository(fetch, pushes, issue):
    repo, problems = checks.forge_problems(fetch, pushes, issue)
    assert repo is None and problems


@pytest.mark.parametrize(
    "body",
    [
        "Closes #12",
        "this fixes #3 too",
        "Resolved: #4",
        "fix owner/repo#9",
        "closes https://example.invalid/o/r/issues/5",
    ],
)
def test_body_refuses_issue_closing_keywords(body):
    assert checks.closing_directives(f"## Summary\n\n{body}\n\nRefs #27\n")


def test_body_allows_refs_and_ordinary_words():
    body = "Fixed the C408 findings; closes nothing.\n\nRefs #27\n"
    assert checks.closing_directives(body) == []
