#!/usr/bin/env python3
"""Model lists and roster check for the delegation skill.

Commands:
  refresh codex-cli|claude-cli       rebuild .delegation/models/<vendor>.json
  list <vendor>                      print each model and its efforts
  check <vendor> <model> [--effort]  exit 0 when listed, 1 when not
  roster                             validate .delegation/roster.toml
  ran codex-cli <session-id>         print the model, effort and sandbox that ran
  ran claude-cli <result.json>       print the models a Claude run reported

Stdlib only: the skill ships in a plugin.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]
# (url, headers) -> parsed JSON body
Fetcher = Callable[[str, dict[str, str]], Any]

SKILL_DIR = Path(__file__).resolve().parent.parent
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
TIME_RE = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9-]+$")
DEFAULT_MAX_AGE_DAYS = 7
COMMAND_TIMEOUT = 60.0
# Allowed clock skew before a timestamp counts as "in the future".
CLOCK_SKEW = timedelta(minutes=5)
REFRESH_HINT = "run: models.py refresh codex-cli"
NO_SERVER_HINT = (
    "no server-fetched Codex catalog: sign in to Codex and run: "
    "models.py refresh codex-cli"
)
NO_SERVER_SOURCE = "codex debug models (no server fetch evidence)"
NO_CLAUDE_KEY = (
    "no ANTHROPIC_API_KEY: the reviewed seed vendors/claude-cli/models.json is used"
)
MODELS_API_URL = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2026-10-21"
CLAUDE_EFFORTS = ("low", "medium", "high", "xhigh", "max")
CLI_VENDORS = ("codex-cli", "claude-cli")
T3_KEYS = {"vendor", "model", "options"}
CLI_KEYS = {"vendor", "model", "effort"}
NOT_REFRESHABLE = {
    "t3": "t3 has no list file: its live list is the orchestrator_capabilities tool",
}


class ModelsError(Exception):
    """A failure with its exit code."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def default_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, capture_output=True, text=True, check=False, timeout=COMMAND_TIMEOUT
    )


def default_fetcher(url: str, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=COMMAND_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise ModelsError(f"Models API returned {exc.code}: {_tail(body)}", 2) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ModelsError(f"Models API request failed: {exc}", 2) from exc
    except json.JSONDecodeError as exc:
        raise ModelsError(f"Models API did not return JSON: {exc}", 2) from exc


def _tail(text: str, lines: int = 10) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def _run(runner: Runner, cmd: list[str]) -> str:
    try:
        result = runner(cmd)
    except FileNotFoundError as exc:
        raise ModelsError(f"{cmd[0]} not found on PATH", 2) from exc
    except subprocess.TimeoutExpired as exc:
        raise ModelsError(
            f"`{' '.join(cmd)}` timed out after {exc.timeout:g}s", 2
        ) from exc
    if result.returncode != 0:
        tail = _tail(result.stderr or "")
        raise ModelsError(f"`{' '.join(cmd)}` exited {result.returncode}:\n{tail}", 2)
    return result.stdout


def parse_time(value: object) -> datetime | None:
    """Parse an RFC 3339 UTC stamp (`Z`, optional fraction of any length)."""
    match = TIME_RE.match(value) if isinstance(value, str) else None
    if not match:
        return None
    try:
        stamp = datetime.fromisoformat(match.group(1) + "+00:00")
    except ValueError:
        return None
    fraction = (match.group(2) or "")[:6].ljust(6, "0")
    return stamp.replace(microsecond=int(fraction))


def _check_time(value: object, label: str, path: Path, now: datetime) -> datetime:
    stamp = parse_time(value)
    if stamp is None:
        raise ModelsError(f"{path}: {label} is not an RFC 3339 UTC time: {value!r}")
    if stamp > now + CLOCK_SKEW:
        raise ModelsError(f"{path}: {label} {value} is in the future")
    return stamp


def validate_list(data: Any, path: Path, vendor: str, now: datetime) -> dict[str, Any]:
    """Validate a whole list file; every failure is a ModelsError."""
    if not isinstance(data, dict):
        raise ModelsError(f"{path}: not a JSON object")
    if data.get("vendor") != vendor:
        raise ModelsError(f"{path}: vendor is {data.get('vendor')!r}, not {vendor}")
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise ModelsError(f"{path}: models must be a non-empty list")
    seen: set[str] = set()
    for entry in models:
        model_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(model_id, str) or not model_id:
            raise ModelsError(f"{path}: a model has no id")
        if model_id in seen:
            raise ModelsError(f"{path}: duplicate model id {model_id}")
        seen.add(model_id)
        efforts = entry.get("efforts")
        if not isinstance(efforts, list) or not all(
            isinstance(e, str) and e for e in efforts
        ):
            raise ModelsError(f"{path}: model {model_id} efforts must be strings")
    if "refreshed_at" in data:
        _check_time(data["refreshed_at"], "refreshed_at", path, now)
    if data.get("source_fetched_at") is not None:
        _check_time(data["source_fetched_at"], "source_fetched_at", path, now)
    if "reviewed" in data:
        try:
            reviewed = date.fromisoformat(str(data["reviewed"]))
        except ValueError as exc:
            raise ModelsError(f"{path}: reviewed is not a date") from exc
        if reviewed > now.date():
            raise ModelsError(f"{path}: reviewed {reviewed} is in the future")
    return data


def parse_codex_models(text: str) -> tuple[list[dict[str, Any]], int]:
    """Return the visible models and the hidden count from `codex debug models`."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelsError(f"codex debug models did not return JSON: {exc}", 2) from exc
    entries = data.get("models") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ModelsError("codex debug models returned no models", 2)
    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    hidden = 0
    for entry in entries:
        slug = entry.get("slug") if isinstance(entry, dict) else None
        if not isinstance(slug, str) or not slug:
            raise ModelsError("codex model entry has no slug", 2)
        if slug in seen:
            raise ModelsError(f"duplicate codex model id: {slug}", 2)
        seen.add(slug)
        if entry.get("visibility") == "hide":
            hidden += 1
            continue
        levels = entry.get("supported_reasoning_levels")
        if not isinstance(levels, list) or not all(
            isinstance(lv, dict) for lv in levels
        ):
            raise ModelsError(f"codex model {slug} has a malformed reasoning level", 2)
        efforts = [lv.get("effort") for lv in levels]
        if not efforts or not all(isinstance(e, str) and e for e in efforts):
            raise ModelsError(f"codex model {slug} has no efforts", 2)
        models.append({"id": slug, "efforts": efforts})
    if not models:
        raise ModelsError("codex debug models returned no visible models", 2)
    return models, hidden


def parse_claude_models(pages: list[Any]) -> list[dict[str, Any]]:
    """Active models and their supported efforts from Models API pages."""
    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in pages:
        for item in page.get("data", []) if isinstance(page, dict) else []:
            model_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(model_id, str) or not model_id:
                raise ModelsError("Models API entry has no id", 2)
            if item.get("lifecycle") != "active" or model_id in seen:
                continue
            seen.add(model_id)
            caps = item.get("capabilities")
            effort = caps.get("effort") if isinstance(caps, dict) else None
            efforts = (
                [lv for lv in CLAUDE_EFFORTS if _supported(effort.get(lv))]
                if isinstance(effort, dict) and _supported(effort.get("supported"))
                else []
            )
            models.append({"id": model_id, "efforts": efforts})
    if not models:
        raise ModelsError("Models API returned no active models", 2)
    return models


def _supported(value: object) -> bool:
    if isinstance(value, dict):
        return value.get("supported") is True
    return value is True


def list_path(root: Path, vendor: str) -> Path:
    return root / ".delegation" / "models" / f"{vendor}.json"


def codex_home(env: Mapping[str, str]) -> Path:
    return Path(env.get("CODEX_HOME") or Path.home() / ".codex")


def _catalog_signature(entries: object) -> list[tuple[Any, Any, list[Any]]] | None:
    """Per model, in order: slug, visibility and reasoning effort list."""
    if not isinstance(entries, list):
        return None
    signature: list[tuple[Any, Any, list[Any]]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return None
        levels = entry.get("supported_reasoning_levels")
        efforts = (
            [lv.get("effort") if isinstance(lv, dict) else None for lv in levels]
            if isinstance(levels, list)
            else None
        )
        signature.append((entry.get("slug"), entry.get("visibility"), efforts or []))
    return signature


def codex_source_fetched_at(
    home: Path, now: datetime, cli_version: str, printed: str
) -> tuple[str | None, str]:
    """The cache's server `fetched_at` and the source line.

    The stamp counts only when the cache was written by the installed CLI and
    holds the catalog `codex debug models` printed; otherwise it is None.
    """
    try:
        cache = json.loads((home / "models_cache.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, NO_SERVER_SOURCE
    if not isinstance(cache, dict):
        return None, NO_SERVER_SOURCE
    value = cache.get("fetched_at")
    stamp = parse_time(value)
    if stamp is None or stamp > now + CLOCK_SKEW:
        return None, NO_SERVER_SOURCE
    installed = cli_version.split()[-1] if cli_version.split() else ""
    cached = cache.get("client_version")
    if cached != installed:
        return None, (
            f"codex debug models (cache client_version {cached!r} is not "
            f"the installed {installed!r}; no server fetch evidence)"
        )
    printed_models = json.loads(printed).get("models")
    expected = _catalog_signature(printed_models)
    if expected is None or _catalog_signature(cache.get("models")) != expected:
        return None, (
            "codex debug models (printed catalog does not match the cache; "
            "no server fetch evidence)"
        )
    return str(value), "codex debug models"


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def refresh_claude(
    env: Mapping[str, str], fetcher: Fetcher, now: datetime
) -> dict[str, Any]:
    key = env.get("ANTHROPIC_API_KEY")
    if not key:
        raise ModelsError(NO_CLAUDE_KEY, 2)
    headers = {"anthropic-version": ANTHROPIC_VERSION, "Authorization": f"Bearer {key}"}
    pages: list[Any] = []
    params = {"limit": "1000"}
    while True:
        page = fetcher(f"{MODELS_API_URL}?{urllib.parse.urlencode(params)}", headers)
        pages.append(page)
        if not (isinstance(page, dict) and page.get("has_more")):
            break
        last = page.get("last_id")
        if not isinstance(last, str) or not last or last == params.get("after_id"):
            raise ModelsError("Models API has_more without a new last_id", 2)
        params["after_id"] = last
    stamp = now.strftime(TIME_FORMAT)
    return {
        "vendor": "claude-cli",
        "source": "Models API",
        "refreshed_at": stamp,
        "source_fetched_at": stamp,
        "models": parse_claude_models(pages),
    }


def refresh(
    root: Path,
    vendor: str,
    runner: Runner,
    now: datetime,
    env: Mapping[str, str],
    fetcher: Fetcher,
) -> dict[str, Any]:
    if vendor == "claude-cli":
        payload = refresh_claude(env, fetcher, now)
    elif vendor == "codex-cli":
        version = _run(runner, ["codex", "--version"]).strip()
        printed = _run(runner, ["codex", "debug", "models"])
        models, hidden = parse_codex_models(printed)
        fetched, source = codex_source_fetched_at(
            codex_home(env), now, version, printed
        )
        payload = {
            "vendor": "codex-cli",
            "source": source,
            "cli_version": version,
            "refreshed_at": now.strftime(TIME_FORMAT),
            "source_fetched_at": fetched,
            "hidden": hidden,
            "models": models,
        }
    else:
        reason = NOT_REFRESHABLE.get(vendor, f"unknown vendor {vendor}")
        raise ModelsError(f"{vendor} is not refreshable; {reason}", 2)
    _write_atomic(list_path(root, vendor), payload)
    return payload


def _read_list(path: Path, vendor: str, now: datetime) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelsError(f"{path} is not readable JSON: {exc}") from exc
    return validate_list(data, path, vendor, now)


def _age(data: dict[str, Any], now: datetime) -> timedelta | None:
    stamp = parse_time(data.get("source_fetched_at"))
    return None if stamp is None else now - stamp


def load_list(
    vendor: str,
    root: Path,
    skill_dir: Path,
    now: datetime,
    max_age_days: float,
    strict: bool = True,
) -> tuple[dict[str, Any], str]:
    """Load a vendor list and say where it came from.

    `strict=False` lets `list` show a stale or unverified Codex list.
    """
    max_age = timedelta(days=max_age_days)
    if vendor == "codex-cli":
        path = list_path(root, vendor)
        if not path.is_file():
            raise ModelsError(f"no codex-cli list at {path}; {REFRESH_HINT}")
        data = _read_list(path, vendor, now)
        age = _age(data, now)
        if strict and age is None:
            raise ModelsError(NO_SERVER_HINT)
        if strict and age is not None and age > max_age:
            raise ModelsError(
                f"codex-cli list is {age.days} days old (max {max_age_days:g}); "
                f"{REFRESH_HINT}"
            )
        fetched = data.get("source_fetched_at") or "no server fetch evidence"
        return data, f"generated list, server fetched {fetched}"
    if vendor == "claude-cli":
        path = list_path(root, vendor)
        note = ""
        if path.is_file():
            data = _read_list(path, vendor, now)
            age = _age(data, now)
            if age is not None and age <= max_age:
                return data, f"generated list, fetched {data['source_fetched_at']}"
            note = "; generated list is stale"
        seed = skill_dir / "vendors" / "claude-cli" / "models.json"
        if not seed.is_file():
            raise ModelsError(f"no claude-cli seed at {seed}")
        data = _read_list(seed, vendor, now)
        return data, f"reviewed seed, reviewed {data.get('reviewed', 'unknown')}{note}"
    if vendor == "t3":
        raise ModelsError("t3 has no list: check against orchestrator_capabilities", 2)
    raise ModelsError(f"unknown vendor {vendor}", 2)


def check_model(
    data: dict[str, Any], vendor: str, model: str, effort: str | None
) -> str:
    """Return an ok line, or raise ModelsError naming what is not listed."""
    for entry in data["models"]:
        if entry["id"] == model:
            if effort is not None and effort not in entry["efforts"]:
                raise ModelsError(
                    f"{vendor} model {model} does not list effort {effort}"
                )
            suffix = f" effort {effort}" if effort is not None else ""
            return f"ok: {vendor} {model}{suffix}"
    raise ModelsError(f"{vendor} does not list model {model}")


def _has_contract(base: Path, name: str, kind: str, relative: str) -> bool:
    """True when `base/relative` is a file that resolves inside `base`."""
    if not NAME_RE.match(name):
        raise ModelsError(f"invalid {kind} name {name!r} (want [a-z][a-z0-9-]*)")
    path = (base / relative).resolve()
    depth = len(Path(relative).parts)
    return path.is_file() and path.parents[depth - 1] == base.resolve()


def _check_row(
    role: str,
    row: Any,
    root: Path,
    skill_dir: Path,
    now: datetime,
    max_age_days: float,
) -> str:
    roles_dir = skill_dir / "roles"
    if not _has_contract(roles_dir, role, "role", f"{role}.md"):
        raise ModelsError(f"unknown role (no roles/{role}.md)")
    if not isinstance(row, dict):
        raise ModelsError("row is not a table")
    vendor = row.get("vendor")
    if not isinstance(vendor, str) or not vendor:
        raise ModelsError("missing vendor")
    vendors_dir = skill_dir / "vendors"
    if not _has_contract(vendors_dir, vendor, "vendor", f"{vendor}/dispatch.md"):
        raise ModelsError(f"unknown vendor {vendor} (no vendors/{vendor}/dispatch.md)")
    allowed, required = (
        (T3_KEYS, ("model",)) if vendor == "t3" else (CLI_KEYS, ("model", "effort"))
    )
    extra = sorted(set(row) - allowed)
    if extra:
        raise ModelsError(f"unknown key(s) for {vendor}: {', '.join(extra)}")
    for key in required:
        if not isinstance(row.get(key), str) or not row[key]:
            raise ModelsError(f"missing or non-string {key}")
    if vendor == "t3":
        options = row.get("options", {})
        if not isinstance(options, dict) or not all(
            isinstance(v, str | bool) for v in options.values()
        ):
            raise ModelsError("options must be a table of string or boolean values")
        return f"shape ok: t3 {row['model']}; check against orchestrator_capabilities"
    if vendor not in CLI_VENDORS:
        raise ModelsError(f"vendor {vendor} has no model list to check against")
    data, origin = load_list(vendor, root, skill_dir, now, max_age_days)
    return f"{check_model(data, vendor, row['model'], row['effort'])} ({origin})"


def check_roster(
    root: Path, skill_dir: Path, now: datetime, max_age_days: float
) -> list[tuple[str, bool, str]]:
    path = root / ".delegation" / "roster.toml"
    if not path.is_file():
        raise ModelsError(f"no roster at {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ModelsError(f"{path} is not valid TOML: {exc}") from exc
    extra = sorted(set(data) - {"roles"})
    if extra:
        raise ModelsError(f"{path}: unknown top-level key(s): {', '.join(extra)}")
    roles = data.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise ModelsError(f"{path} has no [roles.<name>] tables")
    results: list[tuple[str, bool, str]] = []
    for role, row in roles.items():
        try:
            results.append(
                (role, True, _check_row(role, row, root, skill_dir, now, max_age_days))
            )
        except ModelsError as exc:
            results.append((role, False, str(exc)))
    return results


def ran_codex(session_id: str, env: Mapping[str, str]) -> list[str]:
    """Model, effort and sandbox from a Codex session's last turn_context."""
    if not SESSION_ID_RE.match(session_id):
        raise ModelsError(f"invalid codex session id {session_id!r}")
    sessions = codex_home(env) / "sessions"
    files = sorted(sessions.glob(f"**/rollout-*-{session_id}.jsonl"))
    if not files:
        raise ModelsError(f"no codex session {session_id} under {sessions}")
    context: dict[str, Any] | None = None
    with files[-1].open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and record.get("type") == "turn_context":
                payload = record.get("payload")
                if isinstance(payload, dict):
                    context = payload
    if context is None:
        raise ModelsError(f"{files[-1]} has no turn_context record")
    sandbox = context.get("sandbox_policy")
    sandbox_type = sandbox.get("type") if isinstance(sandbox, dict) else None
    return [
        f"session: {files[-1]}",
        f"model: {context.get('model') or '(not recorded)'}",
        f"effort: {context.get('effort') or '(not recorded)'}",
        f"sandbox: {sandbox_type or '(not recorded)'}",
    ]


def ran_claude(result_path: Path) -> tuple[list[str], bool]:
    """Models, error state and subtype from Claude's `--output-format json`."""
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelsError(f"{result_path} is not readable JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelsError(f"{result_path}: not a Claude JSON result object")
    usage = data.get("modelUsage")
    model_ids = sorted(usage) if isinstance(usage, dict) else []
    is_error = data.get("is_error")
    lines = [
        f"session_id: {data.get('session_id') or '(not reported)'}",
        f"models: {', '.join(model_ids) or '(none reported)'}",
        f"is_error: {json.dumps(is_error)}",
        f"subtype: {data.get('subtype')}",
        "effort: requested-but-unverified (not reported)",
    ]
    return lines, bool(model_ids) and is_error is not True


def _default_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=COMMAND_TIMEOUT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return Path.cwd()
    out = result.stdout.strip()
    return Path(out) if result.returncode == 0 and out else Path.cwd()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "--root", type=Path, help="repo root (default: git toplevel or cwd)"
    )
    parser.add_argument("--max-age-days", type=float, default=DEFAULT_MAX_AGE_DAYS)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh").add_argument("vendor")
    sub.add_parser("list").add_argument("vendor")
    check = sub.add_parser("check")
    check.add_argument("vendor")
    check.add_argument("model")
    check.add_argument("--effort")
    sub.add_parser("roster")
    ran = sub.add_parser("ran")
    ran.add_argument("vendor", choices=CLI_VENDORS)
    ran.add_argument("target", help="codex session id, or a Claude result.json path")
    return parser


def main(
    argv: Sequence[str] | None = None,
    runner: Runner = default_runner,
    skill_dir: Path = SKILL_DIR,
    now: datetime | None = None,
    env: Mapping[str, str] | None = None,
    fetcher: Fetcher = default_fetcher,
) -> int:
    args = _parser().parse_args(argv)
    root: Path = args.root or _default_root()
    now = now or datetime.now(UTC)
    env = os.environ if env is None else env
    try:
        if args.cmd == "refresh":
            payload = refresh(root, args.vendor, runner, now, env, fetcher)
            hidden = f", {payload['hidden']} hidden" if "hidden" in payload else ""
            version = f" ({payload['cli_version']})" if "cli_version" in payload else ""
            print(
                f"wrote {list_path(root, args.vendor)}: {len(payload['models'])} "
                f"models{hidden}{version}; source: {payload['source']}; "
                f"source_fetched_at: {payload['source_fetched_at']}"
            )
        elif args.cmd == "list":
            data, origin = load_list(
                args.vendor, root, skill_dir, now, args.max_age_days, strict=False
            )
            print(f"# {args.vendor} ({origin})")
            for entry in data["models"]:
                print(f"{entry['id']}: {', '.join(entry['efforts'])}")
        elif args.cmd == "check":
            data, origin = load_list(
                args.vendor, root, skill_dir, now, args.max_age_days
            )
            line = check_model(data, args.vendor, args.model, args.effort)
            print(f"{line} ({origin})")
        elif args.cmd == "ran":
            if args.vendor == "codex-cli":
                lines, ok = ran_codex(args.target, env), True
            else:
                lines, ok = ran_claude(Path(args.target))
            print("\n".join(lines))
            return 0 if ok else 1
        else:
            results = check_roster(root, skill_dir, now, args.max_age_days)
            for role, ok, message in results:
                print(f"{role}: {'ok' if ok else 'FAIL'}: {message}")
            return 0 if all(ok for _, ok, _ in results) else 1
    except ModelsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
