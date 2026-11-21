"""Spec criteria Outbound (create, link, background), Only the link and Private, plus the
carried case: deferred and excluded beads through `pr` with out-of-scope types allowed."""

from __future__ import annotations

import re

import pytest

from tests.mirror._harness import ACCOUNT, Mirror, assert_only_links_changed, banner

pytestmark = pytest.mark.bd


def test_outbound_creates_one_issue_with_banner_text_and_label_and_links_it(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead(
        "Export widgets", "feature", "-d", "Export as CSV.", "--acceptance", "It opens."
    )
    before = mirror.store_snapshot()

    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    (issue,) = mirror.fake.issues()
    assert issue["author"] == ACCOUNT and issue["title"] == "Export widgets"
    lines = issue["body"].split("\n")
    assert lines[0] == banner(mirror.project_id, bead)
    assert (
        lines[1].startswith(f"> Generated from bead `{bead}`") and "comment" in lines[1]
    )
    assert issue["body"].endswith("\n\nExport as CSV.\n\n## Acceptance\n\nIt opens.")
    assert issue["labels"] == ["bead-type:feature"]
    url = f"https://github.com/acme/widgets/issues/{issue['number']}"
    assert mirror.beads()[bead]["external_ref"] == url
    assert_only_links_changed(before, mirror.store_snapshot(), {bead})
    link_writes = [c for c in mirror.bd_calls() if c.startswith("update ")]
    assert len(link_writes) == 1
    assert link_writes[0].startswith(
        f"update {bead} --external-ref {url} --actor bead-mirror:"
    )

    linked = mirror.store_snapshot()
    writes = len(mirror.fake.writes())
    assert mirror.run("outbound").returncode == 0
    assert len(mirror.fake.writes()) == writes, "a second run makes no writes"
    assert mirror.store_snapshot() == linked


def test_outbound_background_run_creates_nothing(mirror: Mirror) -> None:
    mirror.write_switch()
    mirror.create_bead("Export widgets")
    before = mirror.store_snapshot()
    proc = mirror.run("outbound", "--no-create")
    assert proc.returncode == 0, proc.stderr
    assert "1 eligible bead(s) not yet published" in proc.stdout
    assert mirror.fake.writes() == [] and mirror.fake.issues() == []
    assert mirror.store_snapshot() == before


def test_outbound_background_run_creates_nothing_for_a_bead_held_after_a_refusal(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Poisoned title")
    mirror.fake.set_fault("refuse_create_titled", "Poisoned")
    refused = mirror.run("outbound")
    assert f"held: {bead}: create refused" in refused.stdout
    mirror.fake.set_fault("refuse_create_titled", None)  # the next create would work

    before = mirror.store_snapshot()
    proc = mirror.run("outbound", "--no-create")
    assert proc.returncode == 0, proc.stderr
    assert "1 eligible bead(s) not yet published" in proc.stdout
    assert mirror.fake.creates() == 0 and mirror.fake.issues() == []
    assert mirror.store_snapshot() == before
    assert mirror.run("outbound").returncode == 0 and mirror.fake.creates() == 1


def test_outbound_type_label_is_created_once_and_reused(mirror: Mirror) -> None:
    mirror.write_switch()
    mirror.create_bead("One", "feature")
    mirror.create_bead("Two", "feature")
    mirror.create_bead("Three", "bug")
    assert mirror.run("outbound").returncode == 0
    labels = [c for c in mirror.fake.writes() if c["write"] == "createLabel"]
    assert len(labels) == 2
    assert sorted(i["labels"][0] for i in mirror.fake.issues()) == [
        "bead-type:bug",
        "bead-type:feature",
        "bead-type:feature",
    ]


def test_private_beads_are_not_published_and_mentions_are_code_spans(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    for kind in ("task", "spike", "decision"):
        mirror.create_bead(f"A {kind}", kind)
    mirror.create_bead("Deferred", "feature", "-s", "deferred")
    closed = mirror.create_bead("Closed before opt-in", "bug")
    mirror.bd("close", closed, "--reason", "done")
    mirror.create_bead("Excluded", "feature", "--metadata", '{"mirror":"never"}')
    in_body = mirror.create_bead(
        "Read the notes", "feature", "-d", "See /home/alice/notes.txt first."
    )
    in_title = mirror.create_bead("Fix 192.168.1.20:8080 timeouts", "bug")
    bare_home = mirror.create_bead(
        "Run it", "feature", "-d", "Run it from /home/alice or /Users/bob."
    )
    token = "ghp_" + "x" * 36
    in_acceptance = mirror.create_bead(
        "Use the token", "feature", "--acceptance", f"Works with {token}."
    )
    public = mirror.create_bead(
        "Ask @alice",
        "feature",
        "-d",
        "Ping @alice about #12; keep `@bob` as is. Also _ping @carol_ and _#13_.",
    )
    before = mirror.store_snapshot()

    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    (issue,) = mirror.fake.issues()
    assert issue["title"] == "Ask `@alice`"
    assert (
        "Ping `@alice` about `#12`; keep `@bob` as is. Also _ping `@carol`_ and _`#13`_."
        in issue["body"]
    )
    assert f"held: {in_body}: not published: the body holds a home" in proc.stdout
    assert (
        f"held: {in_title}: not published: the title holds a private IP" in proc.stdout
    )
    assert f"held: {bare_home}: not published: the body holds a home" in proc.stdout
    assert (
        f"held: {in_acceptance}: not published: the body holds something that looks "
        "like a credential" in proc.stdout
    )
    assert "/home/alice" not in proc.stdout + proc.stderr
    assert token not in proc.stdout + proc.stderr
    assert_only_links_changed(before, mirror.store_snapshot(), {public})

    again = mirror.run("outbound")
    assert f"held: {in_body}" in again.stdout and mirror.fake.creates() == 1


PRIVATE_SAMPLES = {
    "a home or workspace path": [
        "C:\\Users\\bob\\notes",
        "/root/.ssh/config",
        "/data/projects/example/notes.txt",
        "/workspace/app/main.py",
        "/srv/www/site",
    ],
    "a file URL": ["file:///etc/hosts"],
    "an internal hostname": [
        "localhost:3000",
        "build.corp",
        "db.internal",
        "nas.home.arpa",
        "printer.lan",
        "mac.local",
    ],
    "a private IP address": ["10.0.0.5", "172.16.4.2:22"],
    "something that looks like a credential": [
        "sk-" + "a" * 24,
        "github_pat_" + "b" * 24,
        "-----BEGIN OPENSSH PRIVATE KEY-----",
    ],
}


def test_private_each_screen_category_is_held_and_reported_by_label(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    held = {
        mirror.create_bead(
            f"Sample {n}", "feature", "-d", f"Look at {sample} first."
        ): (label, sample)
        for n, (label, sample) in enumerate(
            (label, sample)
            for label, samples in PRIVATE_SAMPLES.items()
            for sample in samples
        )
    }
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    for bead, (label, sample) in held.items():
        assert f"held: {bead}: not published: the body holds {label}" in proc.stdout
        assert sample not in proc.stdout + proc.stderr
    assert mirror.fake.issues() == [] and mirror.fake.writes() == []


@pytest.mark.parametrize(
    ("text", "published"),
    [
        (  # a fence only opens at the start of a line
            "Wrap it in ``` fences and ask @alice to review #12.",
            "Wrap it in \\`\\`\\` fences and ask `@alice` to review `#12`.",
        ),
        (
            "Mark it with ~~~ then ask @alice about #12.",
            "Mark it with ~~~ then ask `@alice` about `#12`.",
        ),
        ("``@alice` please", "\\`\\``@alice`\\` please"),  # unmatched runs are literal
        ("Use `x`@alice now", "Use `x` `@alice` now"),  # spans never merge
        ("\\@alice and \\#3", "`@alice` and `#3`"),  # no escaped span opener
        ("```\n@x\n```\nthen @y", "```\n@x\n```\nthen `@y`"),
        ("Run:\n  ~~~sh\n@x\n~~~~\n@y", "Run:\n  ~~~sh\n@x\n~~~~\n`@y`"),
        # GitHub mentions after any non-word character.
        ("Typo: @@alice please look", "Typo: @`@alice` please look"),
        (
            "Reviewers: team-@alice, docs/@alice now",
            "Reviewers: team-`@alice`, docs/`@alice` now",
        ),
        # An HTML block is raw: no code spans or fences, so <code> tags; tags untouched.
        (
            (
                "<details>\n<summary>Logs</summary>\nping @alice about #12\n</details>"
                "\n\nthen @bob"
            ),
            (
                "<details>\n<summary>Logs</summary>\nping <code>@alice</code> about "
                "<code>#12</code>\n</details>\n\nthen `@bob`"
            ),
        ),
        (
            "<div>\n```\n@alice\n```\n</div>",
            "<div>\n```\n<code>@alice</code>\n```\n</div>",
        ),
        (
            '> <div title="@x">\n> `@bob` and @carol',
            '> <div title="@x">\n> `<code>@bob</code>` and <code>@carol</code>',
        ),
        # Where a mention is not live (an autolinked URL, a tag), links stay intact.
        (
            (
                "See https://medium.com/@alice/post or [b](https://x.com/@bob), "
                '<a href="https://x.com/@c">@c</a>'
            ),
            (
                "See https://medium.com/@alice/post or [b](https://x.com/@bob), "
                '<a href="https://x.com/@c">`@c`</a>'
            ),
        ),
        ("-https://a.com/@alice", "-https://a.com/`@alice`"),  # not autolinked
        # A workspace-root path inside a URL, or a short one, is not held.
        (
            "Docs at https://example.com/data/v1/api and /opt/app",
            "Docs at https://example.com/data/v1/api and /opt/app",
        ),
    ],
)
def test_private_mentions_outside_code_are_code_spans_as_markdown_reads_it(
    mirror: Mirror, text: str, published: str
) -> None:
    mirror.write_switch()
    mirror.create_bead("Fence", "feature", "-d", text)
    assert mirror.run("outbound").returncode == 0
    (issue,) = mirror.fake.issues()
    assert issue["body"].split("\n\n", 1)[1] == published


def test_private_pr_path_refuses_deferred_excluded_and_closed_with_out_of_scope_allowed(
    mirror: Mirror,
) -> None:
    mirror.write_switch(pr_enrol=True)
    refused = {
        mirror.create_bead(
            "Deferred task", "task", "-s", "deferred"
        ): "status is deferred",
        mirror.create_bead(
            "Excluded task", "task", "--metadata", '{"mirror":"never"}'
        ): "excluded (mirror=never)",
        mirror.create_bead(
            "Excluded feature", "feature", "--metadata", '{"mirror":"never"}'
        ): "excluded (mirror=never)",
    }
    closed = mirror.create_bead("Closed task", "task")
    mirror.bd("close", closed, "--reason", "done")
    refused[closed] = "closed and was never published"
    before = mirror.store_snapshot()
    for bead, reason in refused.items():
        proc = mirror.run("outbound", "--bead", bead)
        assert proc.returncode == 9 and reason in proc.stderr, (bead, proc.stderr)
    assert mirror.fake.writes() == [] and mirror.store_snapshot() == before

    task = mirror.create_bead("Open task", "task")
    proc = mirror.run("outbound", "--bead", task)
    assert proc.returncode == 0, proc.stderr
    (issue,) = mirror.fake.issues()
    assert issue["labels"] == ["bead-type:task"]
    assert proc.stdout.splitlines()[-1] == mirror.beads()[task]["external_ref"]


def test_private_pr_enrolment_the_switch_refuses_is_not_published(
    mirror: Mirror,
) -> None:
    mirror.write_switch(pr_enrol=False)
    task = mirror.create_bead("Open task", "task")
    before = mirror.store_snapshot()
    proc = mirror.run("outbound", "--bead", task)
    assert proc.returncode == 9 and "pr_enrol is off" in proc.stderr
    assert mirror.fake.writes() == [] and mirror.store_snapshot() == before


def test_outbound_body_fits_the_budget_with_a_truncation_note(mirror: Mirror) -> None:
    mirror.write_switch()
    plain = mirror.create_bead("Long", "feature", "-d", "é" * 30_000 + "a" * 40_000)
    fenced = mirror.create_bead("Fenced", "feature", "-d", "```\n" + "@x #1\n" * 12_000)
    # Every cut offset lands inside a wrapped mention, or just before or after one.
    mentions = [
        mirror.create_bead(
            f"Mentions {i}", "feature", "-d", "a" * i + " @alice" * 9_000
        )
        for i in range(9)
    ]
    # A cut after an escaped "\\" before an owner/repo#N reference re-wraps it with a
    # doubled backslash and two backticks: three characters over a naive cut.
    # With these ID lengths the cut lands among the digits for some k in the range.
    escaped = [
        mirror.create_bead(
            f"Escaped {k}",
            "feature",
            "--id",
            f"ma-esc{k % 100:02d}",
            "-d",
            "a" * k + " \\o/r#1234567" + "b" * 2000,
        )
        for k in range(59_698, 59_712)
    ]
    assert mirror.run("outbound").returncode == 0
    bodies = {
        i["body"].split("bead=", 1)[1].split(" ", 1)[0]: i["body"]
        for i in mirror.fake.issues()
    }
    for bead in [plain, fenced, *mentions, *escaped]:
        body = bodies[bead]
        note = f"\n\n_Truncated: the full text is in bead `{bead}`._"
        assert len(body) <= 60_000
        assert body.startswith(banner(mirror.project_id, bead))
        assert body.endswith(note)
        text = body[: -len(note)].split("\n", 2)[2]
        assert text.count("`") % 2 == 0, "a cut never leaves a code span open"
        assert "@" not in re.sub(r"```[\s\S]*?```|`[^`\n]*`", "", text), (
            "no bare mention"
        )
    assert bodies[fenced][
        : -len(f"\n\n_Truncated: the full text is in bead `{fenced}`._")
    ].endswith("\n```")


def test_outbound_dry_run_plans_the_create_and_writes_nothing(mirror: Mirror) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    before = mirror.store_snapshot()
    proc = mirror.run("outbound", "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert "create label bead-type:feature" in proc.stdout
    assert f"create an issue for {bead}" in proc.stdout
    assert mirror.fake.writes() == [] and mirror.store_snapshot() == before
    assert "state.json" not in mirror.mirror_files()
