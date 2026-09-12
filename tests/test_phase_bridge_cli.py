"""Normal named-stage entry reaches authenticated landing and sequential closure."""

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tests._fake_bd import InjectedCrash
from tests._foreman import ForemanLab
from tests._supervisor import ChildScript
from tests.test_foreman_main import _bridge_adapter, _bridge_stage
from workflow_interpreter.bridge import PhaseAdapter
from workflow_interpreter.bridge import landing as landing_module
from workflow_interpreter.bridge.command import PhaseBridgeCommandResult
from workflow_interpreter.bridge.landing import LANDING_RECEIPT_FILE, LandingHooks
from workflow_interpreter.bridge.verification import CheckCommand
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.tick import Foreman, RunReport
from workflow_interpreter.schema.models import Outcome


@pytest.mark.parametrize(
    "fault", ("none", "admission", "pre-cas", "cas", "receipt", "relation", "close")
)
def test_two_stages_land_from_normal_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    fault: str,
) -> None:
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    config = lab.config.model_copy(
        update={
            "bridge_checks": (
                CheckCommand(
                    name="source-proof",
                    argv=(
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert Path('src/feature.py').is_file()",
                    ),
                ),
            )
        }
    )
    lab.composition = replace(lab.composition, config=config)
    lab.fake_bd.rows["a"] = _bridge_stage("a", description="first stage")
    lab.fake_bd.rows["b"] = _bridge_stage("b", description="second stage")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    started = []

    def drive(self, root_id, *, poll_s, max_wall_s):
        lab.root = lab.store.reads.load_root(root_id)
        started.append(lab.root.metadata.instance_base_commit)
        lab.profiles.next_script(
            ChildScript(
                marker='{"outcome":"done"}\n',
                effects='{"paths":["src/feature.py"]}',
                write_path="src/feature.py",
                write_body=f"value = {len(started) + 1}\n",
                commit=True,
            )
        )
        assert self.tick(root_id).dispatched
        assert self.tick(root_id).settled
        lab.profiles.next_script(
            ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
        )
        assert self.tick(root_id).dispatched
        assert self.tick(root_id).settled
        ship = self.tick(root_id).opened_gate
        assert ship
        lab.approve(ship, Outcome.APPROVE)
        assert self.tick(root_id).closed_gates == (ship,)
        report = self.tick(root_id)
        assert report.terminal
        return RunReport(ticks=7, report=report)

    monkeypatch.setattr(Foreman, "run", drive)
    armed = True
    real_write = landing_module.write_record
    real_land = PhaseAdapter.land
    real_admit = PhaseAdapter.admit

    def admit(self, stage_id, record, *, root_id):
        nonlocal armed
        result = real_admit(self, stage_id, record, root_id=root_id)
        if armed and fault == "admission":
            armed = False
            raise InjectedCrash("after admission")
        return result

    monkeypatch.setattr(PhaseAdapter, "admit", admit)

    def after_cas(self):
        nonlocal armed
        if armed and fault == "cas":
            armed = False
            raise InjectedCrash("after CAS")
        if armed and fault == "close":
            armed = False
            lab.fake_bd.lose_response_on("close")

    def write(path, record):
        nonlocal armed
        real_write(path, record)
        if (
            armed
            and fault == "pre-cas"
            and path.name == landing_module.LANDING_INTENT_FILE
        ):
            armed = False
            raise InjectedCrash("after intent before CAS")
        if armed and fault == "receipt" and path.name == LANDING_RECEIPT_FILE:
            armed = False
            raise InjectedCrash("after receipt")

    def land(self, stage_id, record):
        nonlocal armed
        result = real_land(self, stage_id, record)
        if armed and fault == "relation":
            armed = False
            raise InjectedCrash("after relation")
        return result

    monkeypatch.setattr(LandingHooks, "after_cas", after_cas)
    monkeypatch.setattr(landing_module, "write_record", write)
    monkeypatch.setattr(PhaseAdapter, "land", land)
    if fault != "none":
        crashed = _entry(lab, "a")
        assert crashed.exit_code == 1
        assert "InjectedCrash" in crashed.report["diagnostic"]
        assert len(started) == (0 if fault == "admission" else 1)
        # Current local configuration must never replace the admitted check policy.
        lab.composition = replace(
            lab.composition, config=config.model_copy(update={"bridge_checks": ()})
        )
    if fault == "receipt":
        record = _bridge_adapter(lab).record("a")
        path = (
            lab.composition.for_root(record.root_id).paths.instance_dir
            / LANDING_RECEIPT_FILE
        )
        original = path.read_bytes()
        malformed = json.loads(original)
        del malformed["policy_digest"]
        path.write_text(json.dumps(malformed))
        refused = _entry(lab, "a")
        assert refused.exit_code == 2
        assert "policy_digest" in refused.report["reason"]
        assert lab.fake_bd.rows["a"]["status"] != "closed"
        path.write_bytes(original)
    if fault == "pre-cas":
        pending = _entry(lab, "a")
        assert pending.exit_code == 2
        assert pending.report["disposition"] == "pending"
        assert pending.report["next_action"] == "--retry-landing"
        assert lab.git.head_commit(cwd=lab.repo) == lab.head
        assert len(started) == 1
        conflict = _entry(lab, "a", "--retry", "--retry-landing")
        assert conflict.exit_code == 2
        first = _entry(lab, "a", "--retry-landing")
        repeated = _entry(lab, "a", "--retry-landing")
        assert repeated.exit_code == 2
        historical = _entry(lab, "a")
        assert historical.exit_code == 0
    else:
        first = _entry(lab, "a")
    assert first.exit_code == 0, first.report
    assert first.report["state"] == (
        "completed" if fault in ("none", "admission", "pre-cas") else "recovered"
    )
    assert len(started) == 1
    lab.composition = replace(lab.composition, config=config)
    landed = lab.git.head_commit(cwd=lab.repo)
    assert not lab.git.status_paths(cwd=lab.repo)
    second = _entry(lab, "b")
    assert second.exit_code == 0, second.report
    assert second.report["state"] == "completed"
    assert started == [lab.head, landed]
    assert all(lab.fake_bd.rows[key]["status"] == "closed" for key in ("a", "b"))


def _entry(lab, stage, *extra):
    codes = []
    _, output = lab.transcript(
        lambda: codes.append(
            main_module.main(
                [
                    "--config",
                    str(lab.repo / "foreman.toml"),
                    "phase-bridge",
                    "phase",
                    stage,
                    *extra,
                ]
            )
        )
    )
    return PhaseBridgeCommandResult(
        exit_code=codes[0],
        report={"diagnostic": output}
        if codes[0] == 1
        else json.loads(output.splitlines()[0]),
    )


def test_missing_policy_refuses_before_admission_writes(tmp_path, monkeypatch):
    lab = ForemanLab(tmp_path)
    lab.fake_bd.rows["a"] = _bridge_stage("a", description="first stage")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    result = _entry(lab, "a")
    assert result.exit_code == 2
    assert "nonempty" in result.report["reason"]
    assert lab.fake_bd.command_count("create") == 0
    assert lab.fake_bd.command_count("update") == 0
    assert "bridge_checks" not in lab.config.model_dump(mode="json")


def test_unexpected_programming_valueerror_is_a_crash(tmp_path, monkeypatch):
    from tests.test_foreman_main import _bridge_lab

    lab = _bridge_lab(tmp_path)
    lab.fake_bd.rows["a"] = _bridge_stage("a", description="first stage")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )

    def broken_run(*args, **kwargs):
        raise ValueError("unexpected implementation bug")

    monkeypatch.setattr(Foreman, "run", broken_run)
    result = _entry(lab, "a")
    assert result.exit_code == 1
    assert "unexpected implementation bug" in result.report["diagnostic"]
