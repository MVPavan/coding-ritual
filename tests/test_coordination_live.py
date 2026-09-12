"""One real Claude/Codex coordination path, run only with ``--run-live``.

This intentionally has no fake profile, injected outcome, or hand-authored
``MemberAdmission``.  It is a host proof: its temporary Git/Beads repository
is disposable, and its fixture-only signing key is never supplied in model
inputs.  It does not claim filesystem read containment for that host key.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.live


def test_real_coordination_lands_design_children_and_integration(
    tmp_path: Path,
) -> None:
    """P5 task 4's single assembled, two-runtime host proof.

    The fixture is deliberately tiny: one Markdown design stage, two disjoint
    ``src/`` writers, one declared doubt/ordinary decision, and one integration
    stage.  The assertions consume CLI output and wrapper/host receipts after
    execution; none supplies a model result or an admission payload.
    """

    engine = Path(__file__).resolve().parents[1]
    required = ("git", "bd", "claude", "codex", "bwrap", "ssh-keygen", "uv")
    for binary in required:
        assert shutil.which(binary), f"P5 live proof requires {binary}"

    template_paths = {
        "basic": engine / "workflows/basic.toml",
        "design": engine / "workflows/design-spec.toml",
        "integration": engine / "workflows/integration.toml",
    }
    for name, path in template_paths.items():
        assert path.is_file(), (
            f"P5 live proof requires canonical {name} template: {path}"
        )

    resume = os.environ.get("WF_COORDINATION_LIVE_RESUME")
    if resume:
        tmp_path = Path(resume).resolve(strict=True)
    original_evidence = tmp_path / "evidence"
    if resume:
        assert original_evidence.is_dir()
        evidence = Path(tempfile.mkdtemp(prefix="continuation-", dir=original_evidence))
    else:
        evidence = original_evidence
        evidence.mkdir()
    repo = tmp_path / "coordination-proof"
    if not resume:
        repo.mkdir()
    wrapper_home = tmp_path / "wrapper"
    signer_dir = wrapper_home / "fixture-signers"
    if not resume:
        signer_dir.mkdir(parents=True)
    config = tmp_path / "foreman.toml"
    doubt_graph = repo / "workflows/doubt.toml"
    independent_target = 'TARGET = "after-child-admission"\n'

    def saved(name: str) -> str:
        """Checkpoint identity only; never substitute cached observations."""
        assert json.loads((original_evidence / f"{name}.exit.json").read_text()) == {
            "exit": 0
        }
        argv = json.loads((original_evidence / f"{name}.argv.json").read_text())
        assert isinstance(argv, list) and argv and all(isinstance(a, str) for a in argv)
        return (original_evidence / f"{name}.stdout").read_text().strip()

    def execute(
        name: str,
        argv: list[str],
        *,
        cwd: Path = repo,
        timeout: float = 660,
    ) -> subprocess.CompletedProcess[str]:
        """Run one host command and retain its unmodified transcript."""

        assert not (evidence / f"{name}.argv.json").exists(), name
        result = subprocess.run(
            argv,
            cwd=cwd,
            env={**os.environ, "PYTHONPATH": str(engine)},
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        (evidence / f"{name}.argv.json").write_text(json.dumps(argv, indent=2))
        (evidence / f"{name}.stdout").write_text(result.stdout)
        (evidence / f"{name}.stderr").write_text(result.stderr)
        (evidence / f"{name}.exit.json").write_text(
            json.dumps({"exit": result.returncode}, indent=2)
        )
        assert result.returncode == 0, (
            f"{name} failed ({result.returncode}); retained evidence is {evidence}\n"
            f"{result.stderr[-3000:]}"
        )
        return result

    def cli(name: str, *arguments: str, timeout: float = 660) -> dict[str, Any]:
        """Exercise only the public foreman CLI and require its JSON response."""

        result = execute(
            name,
            [
                "uv",
                "run",
                "python",
                "-m",
                "workflow_interpreter.foreman",
                "--config",
                str(config),
                *arguments,
            ],
            cwd=engine,
            timeout=timeout,
        )
        reports: list[dict[str, Any]] = []
        for line in result.stdout.splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                reports.append(value)
        assert reports, f"{name} produced no JSON report; evidence is {evidence}"
        return reports[-1]

    def create_root(name: str, graph: Path, instance_key: str) -> str:
        """Use the public create spelling, whose intentionally bare output is a root id."""

        result = execute(
            name,
            [
                "uv",
                "run",
                "python",
                "-m",
                "workflow_interpreter.foreman",
                "--config",
                str(config),
                "create",
                str(graph),
                "--instance-key",
                instance_key,
            ],
            cwd=engine,
            timeout=90,
        )
        root_id = result.stdout.strip()
        assert root_id and "\n" not in root_id
        return root_id

    def bd_create(
        name: str, title: str, kind: str, *, parent: str | None = None
    ) -> str:
        if resume:
            # Only the fixture's two named integration records can be resumed.
            assert name in {"integration-epic", "integration-stage"}
            from workflow_interpreter.bridge.adapter import PhaseAdapter
            from workflow_interpreter.foreman.__main__ import _composition

            composition = _composition(config)
            adapter = PhaseAdapter.from_config(composition.config.bd)
            candidates = [
                row
                for row in composition.store._client.list_beads()
                if row.title == title
                and row.issue_type == kind
                and adapter.show(row.id).parent == parent
            ]
            assert len(candidates) <= 1, candidates
            if candidates:
                record = adapter.show(candidates[0].id)
                assert record.description == title
                (evidence / f"{name}-reused.json").write_text(
                    json.dumps({"id": record.id, "parent": parent, "title": title})
                )
                return record.id
        arguments = [
            "bd",
            "create",
            "--title",
            title,
            "--description",
            title,
            "--type",
            kind,
            "--json",
        ]
        if parent is not None:
            arguments.extend(["--parent", parent])
        payload = json.loads(execute(name, arguments).stdout)
        assert payload.get("description") == title, payload
        identifier = payload.get("id")
        assert isinstance(identifier, str) and identifier, payload
        return identifier

    def root_id_from(report: object) -> str:
        """Find the one root id returned by a public admission/preparation report."""

        found: set[str] = set()

        def visit(value: object) -> None:
            if isinstance(value, dict):
                candidate = value.get("root_id")
                if isinstance(candidate, str) and candidate:
                    found.add(candidate)
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(report)
        assert len(found) == 1, f"expected one root id in public report: {report}"
        return found.pop()

    def approve_open_ship(name: str, root_id: str) -> None:
        """Apply a host-only fixture approval after an actual review/check run."""

        status = cli(f"{name}-ship-status", "status", root_id, timeout=90)
        gates = [
            gate for gate in status.get("open_gates", []) if gate.get("node") == "ship"
        ]
        if resume and not gates:
            from workflow_interpreter.foreman.__main__ import _composition

            recorded = _composition(config).store.reads.list_gates(root_id)
            approved = [
                g
                for g in recorded
                if g.metadata.gate_node == "ship"
                and g.metadata.state.value == "closed"
                and g.metadata.outcome is not None
                and g.metadata.outcome.value == "approve"
            ]
            assert len(approved) == 1, status
            assert status.get("terminal") in {None, "done", "shipped"}, status
            return
        assert len(gates) == 1, status
        gate = gates[0]
        template = gate.get("template")
        inbox = gate.get("inbox")
        assert isinstance(template, str) and isinstance(inbox, str), gate
        assert json.loads(template).get("outcome") == "approve", gate
        template_path = evidence / f"{name}-ship-template.json"
        template_path.write_text(template)
        execute(
            f"{name}-fixture-approve",
            [
                "bash",
                str(engine / "scripts/approve-gate.sh"),
                inbox,
                str(signer_dir / "fixture_gate_key"),
                str(template_path),
            ],
            cwd=engine,
            timeout=90,
        )

    def graph_digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def assert_target_clean(name: str) -> None:
        status = execute(
            name,
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        ).stdout
        assert not status, (
            f"the coordinator target must be clean before bridge work: {status}"
        )

    if not resume:
        # The verifier is pinned before either child admission and stays byte-for-
        # byte stable.  It derives the one allowed target value from immutable Git
        # ancestry, so a child based before the independent edit and integration
        # based after it both face exact—not optional—target assertions.
        (repo / "scripts").mkdir()
        (repo / "src").mkdir()
        (repo / "docs").mkdir()

        initial_target = 'TARGET = "before-child-admission"\n'
        independent_target = 'TARGET = "after-child-admission"\n'
        independent_marker = "P5 independent target edit"

        def write_verifier() -> None:
            (repo / "scripts/verify-feature.sh").write_text(
                "#!/usr/bin/env python3\n"
                "import subprocess\n"
                "from pathlib import Path\n"
                "assert Path('scripts/review-checks.sh').is_file(), 'review check missing'\n"
                "history = subprocess.run(['git', 'log', '--format=%s'], text=True, capture_output=True, check=False).stdout\n"
                "expected = "
                + repr(independent_target)
                + " if "
                + repr(independent_marker)
                + " in history else "
                + repr(initial_target)
                + "\nassert Path('src/independent_target.py').read_text() == expected\n"
            )

        (repo / "src/independent_target.py").write_text(initial_target)
        write_verifier()
        (repo / "scripts/review-checks.sh").write_text(
            "#!/bin/sh\nexec python3 -B scripts/verify-feature.sh\n"
        )
        for script in (
            repo / "scripts/verify-feature.sh",
            repo / "scripts/review-checks.sh",
        ):
            script.chmod(0o755)
        (repo / ".gitignore").write_text(".beads/\n.wf/\n__pycache__/\n")
        (repo / "workflows").mkdir()
        for name, source in template_paths.items():
            shutil.copyfile(source, repo / "workflows" / source.name)

        # P5's only custom graph is a canonical P2 fixture with the newly declared
        # ordinary ``doubt`` trigger.  Its post-decision work is a normal bounded
        # writer, so both admitted children have real, selected contributions.
        # It is admitted through ``children admit``; no MemberAdmission bytes are
        # assembled by this test.
        doubt_graph = repo / "workflows/doubt.toml"
        doubt = (
            engine / "workflow_interpreter/fixtures/valid/bounded-decision.toml"
        ).read_text()
        assert "emit fail_plan immediately" in doubt
        doubt = doubt.replace("emit fail_plan immediately", "emit doubt immediately", 1)
        assert 'outcomes = ["fail_plan", "no_diff"]' in doubt
        doubt = doubt.replace(
            'outcomes = ["fail_plan", "no_diff"]', 'outcomes = ["doubt", "no_diff"]', 1
        )
        assert 'triggers = ["fail_plan",' in doubt
        doubt = doubt.replace('triggers = ["fail_plan",', 'triggers = ["doubt",', 1)
        assert 'from = "assess"\non = "fail_plan"' in doubt
        doubt = doubt.replace(
            'from = "assess"\non = "fail_plan"', 'from = "assess"\non = "doubt"', 1
        )
        work_start = doubt.index('name = "work"')
        work_end = doubt.index("[[node]]", work_start)
        work = doubt[work_start:work_end]
        assert "writes = false" in work and "allowed_paths = []" in work
        assert 'outcomes = ["no_diff"]' in work
        work = work.replace("writes = false", "writes = true", 1)
        work = work.replace("allowed_paths = []", 'allowed_paths = ["src/**"]', 1)
        work = work.replace(
            'instructions = "Compute the sum of integers 1 through 10. Write result.json containing {\\"sum\\":55} into WF_ARTIFACT_DIR, then emit no_diff and empty effects through the normal channels. This result is the useful work after the decision."',
            "instructions = \"Create src/child_doubt.py containing DOUBT = 'resolved', commit it, then emit done and the normal effects channel. This is the useful repository contribution after the ordinary doubt decision.\"",
            1,
        )
        work = work.replace('outcomes = ["no_diff"]', 'outcomes = ["done"]', 1)
        assert "Create src/child_doubt.py" in work and 'outcomes = ["done"]' in work
        doubt = doubt[:work_start] + work + doubt[work_end:]
        assert 'from = "work"\non = "no_diff"\nto = "ship"' in doubt
        doubt = doubt.replace(
            'from = "work"\non = "no_diff"\nto = "ship"',
            'from = "work"\non = "done"\nto = "ship"',
            1,
        )
        doubt_graph.write_text(doubt)

        execute("git-init", ["git", "init", "-q", "-b", "proof-main"])
        execute("git-name", ["git", "config", "user.name", "P5 coordination fixture"])
        execute("git-email", ["git", "config", "user.email", "fixture@example.invalid"])
        # bd init appends its own ignore entries.  Run it before the explicit
        # fixture commit so the ordinary bridge begins from a clean target.
        execute(
            "bd-init",
            [
                "bd",
                "init",
                "--prefix",
                "p5live",
                "--non-interactive",
                "--skip-hooks",
                "--skip-agents",
                "--actor",
                "codex:p5-live",
            ],
        )
        execute(
            "git-initial-stage",
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "add",
                ".gitignore",
                "scripts/review-checks.sh",
                "scripts/verify-feature.sh",
                "src/independent_target.py",
                "workflows/basic.toml",
                "workflows/design-spec.toml",
                "workflows/doubt.toml",
                "workflows/integration.toml",
            ],
        )
        execute(
            "git-initial-commit",
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "commit",
                "-qm",
                "Initialize P5 live fixture",
            ],
        )
        # This compiles and runs before any live runner command.  Its source keeps
        # the deliberately awkward Python-string quoting honest against the
        # initial committed fixture state.
        execute(
            "fixture-verifier-compile",
            ["python3", "-m", "py_compile", "scripts/verify-feature.sh"],
        )
        execute("fixture-verifier-initial", ["scripts/verify-feature.sh"])

        # The fixture key is passed only to this host-side gate helper, never in a
        # workflow input or model prompt.  P1's disclosed T1 boundary does not
        # claim filesystem read containment from host-visible runner processes.
        execute(
            "fixture-keygen",
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "p5-live-fixture-only",
                "-f",
                str(signer_dir / "fixture_gate_key"),
            ],
            cwd=engine,
            timeout=90,
        )
        (signer_dir / "allowed_signers").write_text(
            "p5-live-fixture-only " + (signer_dir / "fixture_gate_key.pub").read_text()
        )
        wrapper_root = (
            wrapper_home / hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:16]
        )
        config = tmp_path / "foreman.toml"
        config.write_text(
            f"""repo_root = {json.dumps(str(repo))}
    wrapper_home = {json.dumps(str(wrapper_home))}
    host = {json.dumps(socket.gethostname())}
    actor = "codex:p5-live"
    bridge_graph = {json.dumps(str(repo / "workflows/design-spec.toml"))}
    [[bridge_checks]]
    name = "fixture-final-tree"
    argv = ["scripts/verify-feature.sh"]
    timeout_s = 120
    [bd]
    workspace = {json.dumps(str(repo))}
    actor = "codex:p5-live"
    [signing]
    allowed_signers_path = {json.dumps(str(signer_dir / "allowed_signers"))}
    [supervisor]
    repo_root = {json.dumps(str(repo))}
    wrapper_root = {json.dumps(str(wrapper_root))}
    host = {json.dumps(socket.gethostname())}
    [roles.implementer]
    profile = "claude"
    model = "claude-opus-5"
    effort = "medium"
    [roles.critic]
    profile = "codex"
    model = "gpt-6-astra"
    effort = "medium"
    """
        )
        (evidence / "fixture-contract.json").write_text(
            json.dumps(
                {
                    "authority": "synthetic fixture-only signer; never production human approval",
                    "models": ["claude-opus-5", "gpt-6-astra"],
                    "graphs": {
                        name: graph_digest(repo / "workflows" / path.name)
                        for name, path in template_paths.items()
                    },
                    "doubt_graph": graph_digest(doubt_graph),
                    "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
                },
                indent=2,
            )
        )

        design_epic = bd_create("design-epic", "P5 fixture design", "epic")
        design_stage = bd_create(
            "design-stage",
            "Create docs/design.md with a short fixture design for two independent src contributions; preserve src/independent_target.py.",
            "task",
            parent=design_epic,
        )
        assert_target_clean("target-clean-before-design-phase-bridge")
        # The design stage lands before the children are admitted, so it proves the
        # ordinary bridge's CAS/closure path separately from source collection.
        design_first = cli(
            "design-phase-bridge", "phase-bridge", design_epic, design_stage
        )
        design_root = root_id_from(design_first)
        approve_open_ship("design", design_root)
        design_landed = cli(
            "design-phase-bridge-land", "phase-bridge", design_epic, design_stage
        )
        assert design_landed.get("state") in {"completed", "recovered"}, design_landed

        # This root is only the finite owner ledger.  It is never driven: the two
        # children below, not an extra owner run, supply every live model process.
        owner_root = create_root("owner-create", doubt_graph, "p5-coordination-owner")
        # Input bytes are pinned by admission; the brief itself must not be an
        # untracked coordinator file in the target that integration later checks.
        basic_brief = evidence / "basic.md"
        basic_brief.write_text(
            "Create src/child_basic.py containing BASIC = 'basic'. Keep the independent target file unchanged."
        )
        basic_graph = repo / "workflows/basic.toml"
        basic = cli(
            "admit-basic",
            "children",
            "admit",
            owner_root,
            "basic",
            "--graph",
            str(basic_graph),
            "--input",
            f"task_brief={basic_brief}",
            timeout=90,
        )
        doubt_child = cli(
            "admit-doubt",
            "children",
            "admit",
            owner_root,
            "doubt",
            "--graph",
            str(doubt_graph),
            timeout=90,
        )
        basic_root, doubt_root = root_id_from(basic), root_id_from(doubt_child)
        assert basic_root != doubt_root

        # Both roots pin the old coordinator base.  The target edit therefore
        # cannot be attributed to either child and must survive integration.
        child_base = execute(
            "child-admission-base", ["git", "rev-parse", "HEAD"]
        ).stdout.strip()
        (repo / "src/independent_target.py").write_text(independent_target)
        execute(
            "independent-target-stage",
            ["git", "add", "src/independent_target.py"],
        )
        execute(
            "independent-target-commit",
            ["git", "commit", "-qm", independent_marker + " after child admission"],
        )
        independent_target_commit = execute(
            "independent-target-head", ["git", "rev-parse", "HEAD"]
        ).stdout.strip()
        assert independent_target_commit != child_base

    else:
        # Resume only the completed design/two-child checkpoint, not arbitrary runs.
        from workflow_interpreter.bridge.adapter import PhaseAdapter
        from workflow_interpreter.foreman.__main__ import _composition

        contract = json.loads((original_evidence / "fixture-contract.json").read_text())
        assert (
            hashlib.sha256(config.read_bytes()).hexdigest() == contract["config_sha256"]
        )
        cfg = tomllib.loads(config.read_text())
        assert Path(cfg["repo_root"]).resolve() == repo
        assert Path(cfg["bd"]["workspace"]).resolve() == repo
        assert Path(cfg["supervisor"]["wrapper_root"]).is_dir()
        assert (signer_dir / "fixture_gate_key").is_file()
        for name, path in template_paths.items():
            assert (
                graph_digest(repo / "workflows" / path.name) == contract["graphs"][name]
            )
        assert graph_digest(doubt_graph) == contract["doubt_graph"]
        design_epic = json.loads(saved("design-epic"))["id"]
        design_stage = json.loads(saved("design-stage"))["id"]
        design_landed = json.loads(saved("design-phase-bridge-land"))
        assert design_landed["state"] in {"completed", "recovered"}
        design_root = root_id_from(design_landed)
        owner_root = saved("owner-create")
        basic = json.loads(saved("admit-basic"))
        doubt_child = json.loads(saved("admit-doubt"))
        basic_root, doubt_root = root_id_from(basic), root_id_from(doubt_child)
        child_base = saved("child-admission-base")
        independent_target_commit = saved("independent-target-head")
        composition = _composition(config)
        adapter = PhaseAdapter.from_config(composition.config.bd)
        design_record = adapter.record(design_stage)
        assert design_record is not None
        assert (design_record.root_id, design_record.epic_id, design_record.state) == (
            design_root,
            design_epic,
            "closed",
        )
        assert design_record.landed_oid == child_base
        assert (
            composition.store.reads.load_root(design_root).metadata.terminal
            == "shipped"
        )
        owner = composition.store.reads.load_root(owner_root)
        assert owner.metadata.instance_key == "p5-coordination-owner"
        state = composition.store.coordination_store().state(owner_root)
        for slot, root_id, admission in (
            ("basic", basic_root, basic),
            ("doubt", doubt_root, doubt_child),
        ):
            root = composition.store.reads.load_root(root_id)
            assert root.metadata.coordination is not None
            assert (
                root.metadata.coordination.owner_id,
                root.metadata.coordination.slot,
                root.metadata.coordination.generation,
            ) == (owner_root, slot, 0)
            assert (
                state.children[slot].root_id == root_id
                and state.active[slot] == root_id
            )
            assert (
                root.metadata.coordination.reservation_id
                == admission["receipt"]["link"]["reservation_id"]
            )
            assert root.metadata.instance_base_commit == child_base
            assert root.definition.content_hash == admission["graph_hash"]
            assert root.metadata.config_signature == admission["config_signature"]
            acts = composition.store.reads.list_activations(root_id)
            assert len(acts) == (1 if slot == "basic" else 2)
            assert all(
                a.metadata.is_completed and a.bead.status == "closed" for a in acts
            )
        assert composition.store.reads.load_root(basic_root).metadata.terminal == "done"
        execute(
            "resume-independent-ancestor",
            [
                "git",
                "merge-base",
                "--is-ancestor",
                child_base,
                independent_target_commit,
            ],
        )
        execute(
            "resume-target-ancestor",
            ["git", "merge-base", "--is-ancestor", independent_target_commit, "HEAD"],
        )
        (evidence / "resume-checkpoint.json").write_text(
            json.dumps(
                {
                    "resumed": True,
                    "original_evidence": str(original_evidence),
                    "design_root": design_root,
                    "owner_root": owner_root,
                    "basic_root": basic_root,
                    "doubt_root": doubt_root,
                    "child_base": child_base,
                    "independent_target_commit": independent_target_commit,
                },
                indent=2,
            )
        )

    def child_status(name: str) -> dict[str, Any]:
        return cli(name, "children", "status", owner_root, timeout=90)

    # A gate wait is deliberately not allowed to consume the entire driver
    # timeout.  Repeated bounded public driver calls leave the sibling running
    # while the doubt child obtains and applies its P2 decision.
    if not resume:
        for attempt in range(12):
            cli(
                f"drive-two-children-{attempt}",
                "children",
                "drive",
                owner_root,
                "--max-concurrent",
                "2",
                "--max-wall",
                "45",
                timeout=75,
            )
            observed = child_status(f"children-after-drive-{attempt}")
            rows = {row.get("slot"): row for row in observed.get("children", [])}
            if rows.get("basic", {}).get("state") == "settled" and str(
                rows.get("doubt", {}).get("attention", "")
            ).startswith("waiting at gate "):
                break
        else:
            pytest.fail(
                "doubt child did not reach its ship gate while basic child settled"
            )

    doubt_status = cli("doubt-status", "status", doubt_root, timeout=90)
    requests = doubt_status.get("coordination", {}).get("requests", [])
    assert len(requests) == 1 and isinstance(requests[0], dict), doubt_status
    doubt_request = requests[0]
    boundary = doubt_request.get("boundary")
    assert isinstance(boundary, dict) and boundary.get("kind") == "doubt", doubt_request
    assert doubt_request.get("state") == "applied", doubt_request
    assert doubt_request.get("response", {}).get("action") == "continue_declared", (
        doubt_request
    )
    decision_root = doubt_request.get("decision_root_id")
    assert isinstance(decision_root, str) and decision_root, doubt_request
    from workflow_interpreter.foreman.__main__ import _composition

    decision_activation = _composition(config).store.reads.load_activation(
        doubt_request["attempt_id"]
    )
    assert decision_activation.metadata.wf_root_id == decision_root
    assert decision_activation.metadata.model == "gpt-6-astra"
    assert decision_activation.metadata.runner_profile == "codex"
    assert (
        decision_activation.metadata.is_completed
        and decision_activation.bead.status == "closed"
    )
    (evidence / "bound-decision-activation.json").write_text(
        decision_activation.metadata.model_dump_json(indent=2)
    )
    approve_open_ship("doubt-child", doubt_root)
    for attempt in range(4):
        cli(
            f"finish-two-children-{attempt}",
            "children",
            "drive",
            owner_root,
            "--max-concurrent",
            "2",
            "--max-wall",
            "45",
            timeout=75,
        )
        observed = child_status(f"children-after-finish-{attempt}")
        rows = {row.get("slot"): row for row in observed.get("children", [])}
        if all(
            rows.get(slot, {}).get("state") in {"settled", "collected"}
            for slot in ("basic", "doubt")
        ):
            break
    else:
        pytest.fail("fixture approval did not settle the doubt child")

    basic_collection = cli(
        "collect-basic", "children", "collect", owner_root, "basic", "0", timeout=90
    )
    doubt_collection = cli(
        "collect-doubt", "children", "collect", owner_root, "doubt", "0", timeout=90
    )
    basic_receipt = basic_collection.get("receipt_digest")
    doubt_receipt = doubt_collection.get("receipt_digest")
    assert isinstance(basic_receipt, str) and len(basic_receipt) == 64, basic_collection
    assert isinstance(doubt_receipt, str) and len(doubt_receipt) == 64, doubt_collection
    assert_target_clean("target-clean-before-integration")

    integration_epic = bd_create("integration-epic", "P5 fixture integration", "epic")
    integration_stage = bd_create(
        "integration-stage",
        "Integrate both collected child contributions; retain docs/design.md and the independently committed src/independent_target.py unchanged.",
        "task",
        parent=integration_epic,
    )
    request = {
        "owner_id": owner_root,
        "epic_id": integration_epic,
        "stage_id": integration_stage,
        "request_key": "p5-two-source-integration",
        "sources": [["basic", 0, basic_receipt], ["doubt", 0, doubt_receipt]],
    }
    request_path = evidence / "integration-request.json"
    request_path.write_text(json.dumps(request, indent=2))
    prepared = cli(
        "integration-prepare",
        "integration",
        "prepare",
        "--request",
        str(request_path),
        timeout=180,
    )
    integration_root = root_id_from(prepared)
    integration_status = cli(
        "integration-status",
        "integration",
        "status",
        integration_epic,
        integration_stage,
        timeout=90,
    )
    assert (
        integration_status["association"]["identity_digest"]
        == prepared["integration_digest"]
    )
    assert integration_status["association"]["receipt"]["root_id"] == integration_root
    assert integration_status["bridge"]["root_id"] == integration_root
    assert integration_status["bridge"]["target_ref"] == "refs/heads/proof-main"
    integration_first = cli(
        "integration-phase-bridge",
        "phase-bridge",
        integration_epic,
        integration_stage,
        timeout=660,
    )
    assert root_id_from(integration_first) == integration_root
    approve_open_ship("integration", integration_root)
    integration_landed = cli(
        "integration-phase-bridge-land",
        "phase-bridge",
        integration_epic,
        integration_stage,
        timeout=180,
    )
    assert integration_landed.get("state") in {"completed", "recovered"}, (
        integration_landed
    )
    execute("final-verifier", ["scripts/verify-feature.sh"], timeout=90)

    from workflow_interpreter.bridge.integration import (
        IntegrationGuard,
        prepared_for_stage,
    )
    from workflow_interpreter.foreman.__main__ import _composition
    from workflow_interpreter.supervisor.models import LaunchReceipt, WorkspaceRecord
    from workflow_interpreter.supervisor.paths import ExecLedger, read_record

    composition = _composition(config)
    association = prepared_for_stage(composition, integration_epic, integration_stage)
    assert association is not None, "lost integration association after landing"
    target_claim = IntegrationGuard(composition).claim(association.target_key)
    assert target_claim is not None, "lost integration target claim after landing"
    (evidence / "integration-control.json").write_text(
        json.dumps(
            {
                "association": association.model_dump(mode="json"),
                "target_claim": target_claim[1].model_dump(mode="json"),
            },
            indent=2,
        )
    )
    pinned_roots = {
        root_id: composition.store.reads.load_root(root_id)
        for root_id in (
            design_root,
            owner_root,
            basic_root,
            doubt_root,
            decision_root,
            integration_root,
        )
    }
    assert pinned_roots[basic_root].metadata.instance_base_commit == child_base
    assert pinned_roots[doubt_root].metadata.instance_base_commit == child_base
    assert association.base_commit == independent_target_commit
    pin_evidence = {
        root_id: {
            "graph_content_hash": root.metadata.graph_content_hash,
            "config_signature": root.metadata.config_signature,
            "instance_inputs": [
                {"name": item.name, "sha256": item.sha256}
                for item in root.metadata.instance_inputs
            ],
        }
        for root_id, root in pinned_roots.items()
    }
    assert all(item["config_signature"] for item in pin_evidence.values())
    (evidence / "canonical-pins.json").write_text(json.dumps(pin_evidence, indent=2))

    def runtime_evidence(root_id: str) -> list[dict[str, object]]:
        """Require real process, session, and backend-model proof per activation."""

        rows: list[dict[str, object]] = []
        for activation in composition.store.reads.list_activations(root_id):
            metadata = activation.metadata
            receipt = read_record(
                composition.for_root(root_id).paths.receipt(activation.activation_id),
                LaunchReceipt,
            )
            assert receipt is not None, (
                f"missing launch receipt for {activation.activation_id}"
            )
            ledger = ExecLedger(
                composition.for_root(root_id).paths.ledger(activation.activation_id)
            ).entries()
            assert len(ledger) == 1 and ledger[0].launch_id == receipt.launch_id, ledger
            assert (receipt.root_id, receipt.activation_id) == (
                root_id,
                activation.activation_id,
            )
            assert ledger[0].activation_id == activation.activation_id
            assert ledger[0].pid == receipt.handle.pid
            assert (
                metadata.handle is not None
                and metadata.handle.session_id == metadata.session_id
            )
            assert receipt.handle.pid == metadata.handle.pid
            assert receipt.handle.proc_start_time == metadata.handle.proc_start_time
            log_path = composition.for_root(root_id).paths.log(activation.activation_id)
            assert Path(receipt.handle.log_path) == log_path
            events = []
            for line in log_path.read_text().splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    events.append(event)
            assert events, f"no runner events for {activation.activation_id}"
            backend: dict[str, object]
            if metadata.runner_profile == "claude":
                init = next(
                    (
                        event
                        for event in events
                        if event.get("type") == "system"
                        and event.get("subtype") == "init"
                        and event.get("session_id") == metadata.session_id
                        and event.get("model") == "claude-opus-5"
                    ),
                    None,
                )
                assert init is not None, (
                    f"missing Claude backend init for {activation.activation_id}"
                )
                backend = {"session_id": init["session_id"], "model": init["model"]}
            elif metadata.runner_profile == "codex":
                thread = next(
                    (
                        event.get("thread_id")
                        for event in events
                        if event.get("type") == "thread.started"
                    ),
                    None,
                )
                assert isinstance(thread, str) and thread, activation.activation_id
                # New Codex sessions are assigned by the backend, not preassigned
                # in the launch handle. Bind the emitted thread to its native
                # rollout and the exact receipt cwd, retaining both identities.
                assert metadata.session_id in ("", thread)
                assert receipt.handle.session_id in ("", thread)
                sessions = (
                    Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
                    / "sessions"
                )
                rollouts = list(sessions.rglob(f"*{thread}*.jsonl"))
                assert len(rollouts) == 1, (
                    f"missing authoritative Codex rollout for {thread}"
                )
                rollout_events = [
                    json.loads(line) for line in rollouts[0].read_text().splitlines()
                ]
                session_meta = [
                    event["payload"]
                    for event in rollout_events
                    if event.get("type") == "session_meta"
                ]
                assert len(session_meta) == 1
                assert session_meta[0]["id"] == thread
                assert (
                    Path(session_meta[0]["cwd"]).resolve()
                    == Path(receipt.cwd).resolve()
                )
                contexts = [
                    event.get("payload", {})
                    for event in rollout_events
                    if event.get("type") == "turn_context"
                ]
                assert any(
                    context.get("model") == "gpt-6-astra" for context in contexts
                ), contexts
                backend = {
                    "thread_id": thread,
                    "rollout": str(rollouts[0]),
                    "session_meta": session_meta[0],
                    "contexts": contexts,
                }
            else:
                pytest.fail(
                    f"live proof used forbidden runner {metadata.runner_profile}"
                )
            workspace = read_record(
                composition.for_root(root_id).paths.workspace_record,
                WorkspaceRecord,
            )
            assert workspace is not None, f"missing workspace record for {root_id}"
            rows.append(
                {
                    "activation": activation.activation_id,
                    "root": root_id,
                    "node": metadata.node,
                    "runner": metadata.runner_profile,
                    "pinned_model": metadata.model,
                    "session": metadata.session_id,
                    "backend_session": backend.get(
                        "thread_id", backend.get("session_id")
                    ),
                    "pid": receipt.handle.pid,
                    "proc_start_time": receipt.handle.proc_start_time,
                    "started_at": receipt.handle.started_at,
                    "ended_at": (
                        metadata.exit_record.ended_at
                        if metadata.exit_record is not None
                        else None
                    ),
                    "worktree": workspace.model_dump(mode="json"),
                    "argv": list(receipt.argv),
                    "backend": backend,
                }
            )
        return rows

    runtime = [
        *runtime_evidence(design_root),
        *runtime_evidence(basic_root),
        *runtime_evidence(doubt_root),
        *runtime_evidence(decision_root),
        *runtime_evidence(integration_root),
    ]
    assert {row["pinned_model"] for row in runtime} == {"claude-opus-5", "gpt-6-astra"}
    decision_runtime = [row for row in runtime if row["root"] == decision_root]
    assert decision_runtime and all(
        row["pinned_model"] == "gpt-6-astra" for row in decision_runtime
    ), decision_runtime
    basic_runs = [row for row in runtime if row["root"] == basic_root]
    doubt_initial_runs = [
        row for row in runtime if row["root"] == doubt_root and row["node"] == "assess"
    ]
    assert len(basic_runs) == 1 and len(doubt_initial_runs) == 1
    child_runs = [*basic_runs, *doubt_initial_runs]
    child_starts = [row["started_at"] for row in child_runs]
    child_ends = [row["ended_at"] for row in child_runs]
    assert all(isinstance(value, str) for value in (*child_starts, *child_ends))
    # A serial driver has its second start at or after the first end.  This
    # interval assertion is the actual overlap proof, not merely a requested
    # ``--max-concurrent 2`` setting.
    assert max(child_starts) < min(child_ends), child_runs
    (evidence / "runtime-identities.json").write_text(
        json.dumps(runtime, indent=2, default=str)
    )

    final_head = execute("final-head", ["git", "rev-parse", "HEAD"]).stdout.strip()
    final_tree = execute(
        "final-tree", ["git", "ls-tree", "-r", "--name-only", "HEAD"]
    ).stdout.splitlines()
    assert {
        "docs/design.md",
        "src/child_basic.py",
        "src/child_doubt.py",
        "src/independent_target.py",
    } <= set(final_tree)
    assert (repo / "src/independent_target.py").read_text() == independent_target
    execute(
        "independent-target-ancestor",
        ["git", "merge-base", "--is-ancestor", independent_target_commit, "HEAD"],
    )
    (evidence / "final-target.json").write_text(
        json.dumps(
            {
                "resumed": bool(resume),
                "original_evidence": str(original_evidence),
                "continuation_evidence": str(evidence) if resume else None,
                "head": final_head,
                "tree": final_tree,
                "design_root": design_root,
                "owner_root": owner_root,
                "decision": doubt_request,
                "decision_root": decision_root,
                "child_roots": {"basic": basic_root, "doubt": doubt_root},
                "collections": {"basic": basic_collection, "doubt": doubt_collection},
                "child_base": child_base,
                "independent_target_commit": independent_target_commit,
                "integration_root": integration_root,
                "integration_status": integration_status,
                "target_claim": target_claim[1].model_dump(mode="json"),
                "landing": integration_landed,
            },
            indent=2,
        )
    )
