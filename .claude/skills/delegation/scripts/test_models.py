"""Lean tests for models.py; temp dirs only, never a real CLI or network."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import models

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
FRESH = "2026-10-30T11:07:30.882173733Z"
SEED = {
    "vendor": "claude-cli",
    "source": "reviewed seed",
    "reviewed": "2026-10-30",
    "models": [{"id": "claude-opus-5-5", "efforts": ["low", "high"]}],
}


def codex_output(*entries: dict[str, object]) -> str:
    return json.dumps({"models": list(entries)})


def entry(slug: str, efforts: list[str], visibility: str = "list") -> dict[str, object]:
    levels = [{"effort": e, "description": ""} for e in efforts]
    return {
        "slug": slug,
        "visibility": visibility,
        "supported_reasoning_levels": levels,
    }


CATALOG = [
    entry("gpt-6.1-sol", ["low", "medium", "high"]),
    entry("gpt-reserve", ["low"], visibility="hide"),
]


def fake_runner(stdout: str) -> models.Runner:
    def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        out = "codex-cli 0.164.0\n" if cmd == ["codex", "--version"] else stdout
        return subprocess.CompletedProcess(cmd, 0, out, "")

    return run


def no_network(url: str, headers: dict[str, str]) -> Any:
    raise AssertionError("network called")


class ModelsTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "repo"
        self.skill = Path(tmp.name) / "skill"
        self.codex_home = Path(tmp.name) / "codex"
        self.codex_home.mkdir()
        self.env: dict[str, str] = {"CODEX_HOME": str(self.codex_home)}
        for role in ("implementer", "reviewer"):
            (self.skill / "roles").mkdir(parents=True, exist_ok=True)
            (self.skill / "roles" / f"{role}.md").write_text("")
        for vendor in ("t3", "codex-cli", "claude-cli"):
            (self.skill / "vendors" / vendor).mkdir(parents=True)
            (self.skill / "vendors" / vendor / "dispatch.md").write_text("")
        (self.skill / "vendors" / "claude-cli" / "models.json").write_text(
            json.dumps(SEED)
        )

    def run_main(
        self,
        *argv: str,
        stdout: str = "",
        now: datetime = NOW,
        fetcher: models.Fetcher = no_network,
    ) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = models.main(
                ["--root", str(self.root), *argv],
                runner=fake_runner(stdout),
                skill_dir=self.skill,
                now=now,
                env=self.env,
                fetcher=fetcher,
            )
        return code, out.getvalue() + err.getvalue()

    def refresh(
        self,
        fetched_at: str | None = FRESH,
        client_version: str = "0.164.0",
        cached: list[dict[str, object]] = CATALOG,
    ) -> tuple[int, str]:
        if fetched_at is not None:
            cache = {
                "fetched_at": fetched_at,
                "client_version": client_version,
                "models": cached,
            }
            (self.codex_home / "models_cache.json").write_text(json.dumps(cache))
        printed = [{**e, "base_instructions": "x"} for e in CATALOG]
        return self.run_main("refresh", "codex-cli", stdout=codex_output(*printed))

    def write_roster(self, text: str) -> None:
        (self.root / ".delegation").mkdir(parents=True, exist_ok=True)
        (self.root / ".delegation" / "roster.toml").write_text(text)

    def test_parse_excludes_hidden(self) -> None:
        found, hidden = models.parse_codex_models(
            codex_output(entry("a", ["low"]), entry("b", ["low"], visibility="hide"))
        )
        self.assertEqual(found, [{"id": "a", "efforts": ["low"]}])
        self.assertEqual(hidden, 1)

    def test_parse_rejects_bad_output(self) -> None:
        null_level: dict[str, object] = {
            "slug": "a",
            "supported_reasoning_levels": [None],
        }
        bad = {
            "non-JSON": "not json",
            "duplicate": codex_output(entry("a", ["low"]), entry("a", ["high"])),
            "no efforts": codex_output(entry("a", [])),
            "empty": codex_output(),
            "null level": codex_output(null_level),
        }
        for label, text in bad.items():
            with self.subTest(label), self.assertRaises(models.ModelsError):
                models.parse_codex_models(text)

    def test_refresh_records_source_time(self) -> None:
        code, out = self.refresh()
        self.assertEqual(code, 0, out)
        self.assertIn("1 models, 1 hidden", out)
        data = json.loads(models.list_path(self.root, "codex-cli").read_text())
        self.assertEqual(data["refreshed_at"], "2026-10-30T12:00:00Z")
        self.assertEqual(data["source_fetched_at"], FRESH)
        self.assertEqual(data["source"], "codex debug models")

    def test_refresh_refuses_unrelated_cache(self) -> None:
        other = [entry("gpt-6.1-sol", ["low", "high"]), CATALOG[1]]
        cases = [
            ("0.163.0", CATALOG, "client_version"),
            ("0.164.0", other, "does not match the cache"),
        ]
        for version, cached, reason in cases:
            with self.subTest(reason):
                code, out = self.refresh(client_version=version, cached=cached)
                self.assertEqual(code, 0, out)
                data = json.loads(models.list_path(self.root, "codex-cli").read_text())
                self.assertIsNone(data["source_fetched_at"])
                self.assertIn(reason, data["source"])
                code, out = self.run_main("check", "codex-cli", "gpt-6.1-sol")
                self.assertEqual(code, 1)
                self.assertIn(models.NO_SERVER_HINT, out)

    def test_codex_freshness_uses_server_fetch(self) -> None:
        cases = [
            (None, models.NO_SERVER_HINT),
            ("2026-10-01T00:00:00.5Z", models.REFRESH_HINT),
        ]
        for fetched_at, hint in cases:
            with self.subTest(fetched_at):
                (self.codex_home / "models_cache.json").unlink(missing_ok=True)
                self.refresh(fetched_at)
                code, out = self.run_main("check", "codex-cli", "gpt-6.1-sol")
                self.assertEqual(code, 1)
                self.assertIn(hint, out)
        data = json.loads(models.list_path(self.root, "codex-cli").read_text())
        self.assertIsNotNone(data["source_fetched_at"])

    def test_check(self) -> None:
        self.refresh()
        cases = [
            (("gpt-6.1-sol", "--effort", "high"), 0, "ok"),
            (("gpt-9",), 1, "does not list model gpt-9"),
            (("gpt-6.1-sol", "--effort", "ultra"), 1, "does not list effort ultra"),
        ]
        for args, want, text in cases:
            with self.subTest(args):
                code, out = self.run_main("check", "codex-cli", *args)
                self.assertEqual(code, want, out)
                self.assertIn(text, out)

    def test_missing_list_message(self) -> None:
        code, out = self.run_main("check", "codex-cli", "gpt-6.1-sol")
        self.assertEqual(code, 1)
        self.assertIn(models.REFRESH_HINT, out)

    def test_command_failures_exit_2(self) -> None:
        def missing(cmd: list[str]) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError(cmd[0])

        def slow(cmd: list[str]) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd, 60)

        for runner in (missing, slow):
            with self.subTest(runner.__name__):
                with contextlib.redirect_stderr(io.StringIO()):
                    code = models.main(
                        ["--root", str(self.root), "refresh", "codex-cli"],
                        runner=runner,
                        now=NOW,
                        env=self.env,
                    )
                self.assertEqual(code, 2)

    def test_list_validation(self) -> None:
        good = {"vendor": "codex-cli", "models": [{"id": "a", "efforts": []}]}
        bad = {
            "vendor": {**good, "vendor": "claude-cli"},
            "empty": {**good, "models": []},
            "duplicate": {**good, "models": [good["models"][0]] * 2},
            "effort type": {**good, "models": [{"id": "a", "efforts": [1]}]},
            "future": {**good, "refreshed_at": "2026-11-30T00:00:00Z"},
            "bad time": {**good, "source_fetched_at": "yesterday"},
        }
        models.validate_list(good, Path("x"), "codex-cli", NOW)
        for label, data in bad.items():
            with self.subTest(label), self.assertRaises(models.ModelsError):
                models.validate_list(data, Path("x"), "codex-cli", NOW)

    def test_claude_refresh_and_source(self) -> None:
        code, out = self.run_main("refresh", "claude-cli")
        self.assertEqual(code, 2)
        self.assertIn("no ANTHROPIC_API_KEY", out)
        code, out = self.run_main("check", "claude-cli", "claude-opus-5-5")
        self.assertEqual(code, 0, out)
        self.assertIn("reviewed seed, reviewed 2026-10-30", out)

        def level(ok: bool) -> dict[str, bool]:
            return {"supported": ok}

        effort = {
            "supported": level(True),
            "low": level(True),
            "medium": level(False),
            "high": level(True),
            "xhigh": None,
            "max": level(True),
        }
        pages = [
            {
                "data": [
                    {
                        "id": "claude-new",
                        "lifecycle": "active",
                        "capabilities": {"effort": effort},
                    },
                    {"id": "claude-old", "lifecycle": "deprecated"},
                ],
                "has_more": True,
                "last_id": "claude-old",
            },
            {
                "data": [{"id": "claude-plain", "lifecycle": "active"}],
                "has_more": False,
            },
        ]
        urls: list[str] = []

        def fetcher(url: str, headers: dict[str, str]) -> Any:
            urls.append(url)
            self.assertEqual(headers["Authorization"], "Bearer k")
            return pages[len(urls) - 1]

        self.env["ANTHROPIC_API_KEY"] = "k"
        code, out = self.run_main("refresh", "claude-cli", fetcher=fetcher)
        self.assertEqual(code, 0, out)
        self.assertIn("after_id=claude-old", urls[1])
        code, out = self.run_main("list", "claude-cli")
        self.assertIn("generated list", out)
        self.assertIn("claude-new: low, high, max\nclaude-plain: \n", out)
        self.assertNotIn("claude-old", out)

    def test_ran_codex(self) -> None:
        sid = "01a18d22-07d9-78c3-a9da-097df90aff2c"
        day = self.codex_home / "sessions" / "2026" / "10" / "30"
        day.mkdir(parents=True)
        context = {
            "type": "turn_context",
            "payload": {
                "model": "gpt-6-luna",
                "effort": "low",
                "sandbox_policy": {"type": "read-only"},
            },
        }
        (day / f"rollout-2026-10-30T14-06-20-{sid}.jsonl").write_text(
            '{"type": "session_meta"}\n' + json.dumps(context) + "\n"
        )
        code, out = self.run_main("ran", "codex-cli", sid)
        self.assertEqual(code, 0, out)
        for text in ("model: gpt-6-luna", "effort: low", "sandbox: read-only"):
            self.assertIn(text, out)
        code, out = self.run_main("ran", "codex-cli", "0000-missing")
        self.assertEqual(code, 1)

    def test_ran_claude(self) -> None:
        result = self.root / "result.json"
        self.root.mkdir()
        cases = [
            (
                {
                    "is_error": False,
                    "subtype": "success",
                    "session_id": "5f0c-sid",
                    "modelUsage": {"claude-haiku-5-5": {}},
                },
                0,
            ),
            (
                {
                    "is_error": True,
                    "subtype": "error_during_execution",
                    "modelUsage": {"claude-haiku-5-5": {}},
                },
                1,
            ),
            ({"is_error": False, "subtype": "success"}, 1),
        ]
        for data, want in cases:
            with self.subTest(data):
                result.write_text(json.dumps(data))
                code, out = self.run_main("ran", "claude-cli", str(result))
                self.assertEqual(code, want, out)
                self.assertIn("effort: requested-but-unverified", out)
                if want == 0:
                    self.assertIn("models: claude-haiku-5-5", out)
                    self.assertIn("session_id: 5f0c-sid", out)

    def test_roster_ok(self) -> None:
        self.refresh()
        self.write_roster(
            "[roles.implementer]\n"
            'vendor = "t3"\nmodel = "claude-opus-5-5"\n'
            'options = { effort = "medium", fastMode = false }\n'
            "[roles.reviewer]\n"
            'vendor = "codex-cli"\nmodel = "gpt-6.1-sol"\neffort = "high"\n'
        )
        code, out = self.run_main("roster")
        self.assertEqual(code, 0, out)
        self.assertIn("check against orchestrator_capabilities", out)

    def test_roster_failures(self) -> None:
        self.refresh()
        sol = 'vendor = "codex-cli"\nmodel = "gpt-6.1-sol"\neffort = "high"'
        cases = {
            "bad effort": ("reviewer", sol.replace('"high"', '"ultra"')),
            "unknown vendor": (
                "reviewer",
                'vendor = "gemini"\nmodel = "x"\neffort = "high"',
            ),
            "vendor traversal": ("reviewer", sol.replace("codex-cli", "../roles")),
            "unknown role": ("critic", sol),
            "role traversal": ('"../SKILL"', sol),
            "unknown key": ("reviewer", sol + "\nfast = true"),
        }
        (self.skill / "SKILL.md").write_text("")
        for label, (role, body) in cases.items():
            with self.subTest(label):
                self.write_roster(f"[roles.{role}]\n{body}\n")
                code, out = self.run_main("roster")
                self.assertEqual(code, 1, out)
                self.assertIn(f"{role.strip(chr(34))}: FAIL", out)


if __name__ == "__main__":
    unittest.main()
