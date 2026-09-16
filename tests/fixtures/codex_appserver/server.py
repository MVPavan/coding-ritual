"""Bounded fake of exercised codex-cli 0.154.0 stdio messages; no model calls."""

import json
import os
import sys
import time
from pathlib import Path


def send(value):
    """Write one bounded protocol message."""
    if os.environ.get("WF_ARTIFACT_DIR"):
        with (Path(os.environ["WF_ARTIFACT_DIR"]) / "responses.jsonl").open("a") as log:
            log.write(json.dumps(value) + "\n")
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()


def run_turn_server():
    """Exercise registration, intent, one turn, and EOF shutdown without a model."""
    mode = os.environ.get("WF_RPC_TEST_MODE", "complete")
    artifacts = Path(os.environ["WF_ARTIFACT_DIR"])
    artifacts.mkdir(parents=True, exist_ok=True)
    for line in sys.stdin:
        message = json.loads(line)
        with (artifacts / "requests.jsonl").open("a") as log:
            log.write(line)
        method = message.get("method")
        if method == "initialize":
            if mode == "hang-request":
                time.sleep(60)
            send(
                {
                    "id": message["id"],
                    "result": {
                        "userAgent": "codex-cli/0.154.0",
                        "codexHome": "wrong"
                        if mode == "wrong-home"
                        else os.environ["CODEX_HOME"],
                        "platformFamily": "unix",
                        "platformOs": "linux",
                    },
                }
            )
        elif method in ("thread/start", "thread/resume"):
            params = message["params"]
            send(
                {
                    "id": message["id"],
                    "result": {
                        "thread": {
                            "id": "thread-1",
                            "cliVersion": "0.154.0",
                            "createdAt": 0,
                            "updatedAt": 0,
                            "cwd": params["cwd"],
                            "ephemeral": False,
                            "modelProvider": "openai",
                            "preview": "",
                            "projectId": None,
                            "sessionId": "session-1",
                            "source": "appServer",
                            "status": {"type": "idle"},
                            "turns": [],
                        },
                        "model": params["model"],
                        "modelProvider": "openai",
                        "cwd": params["cwd"],
                        "approvalPolicy": "never",
                        "approvalsReviewer": "user",
                        "sandbox": {
                            "type": "workspaceWrite",
                            "writableRoots": [],
                            "networkAccess": mode == "wrong-policy",
                            "excludeSlashTmp": True,
                            "excludeTmpdirEnvVar": False,
                        },
                    },
                }
            )
        elif method == "turn/start":
            directory = Path(os.environ["WF_OUTCOME_FILE"]).parent.parent
            registration = json.loads((directory / "session.json").read_text())
            intent = json.loads((directory / "turn.json").read_text())
            assert registration["thread_id"] == "thread-1"
            assert intent["phase"] == "intent"
            assert message["params"]["sandboxPolicy"]["networkAccess"] is False
            send(
                {
                    "id": message["id"],
                    "result": {
                        "turn": {
                            "id": "turn-1",
                            "status": "inProgress",
                            "items": [],
                        }
                    },
                }
            )
            Path(os.environ["WF_OUTCOME_FILE"]).write_text('{"outcome":"no_diff"}')
            Path(os.environ["WF_EFFECTS_FILE"]).write_text('{"paths":[]}')
            if mode == "exit-without-turn":
                return
            if mode == "unknown-after-start":
                send({"method": "unknown/permission", "params": {}})
            else:
                send(
                    {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "wrong"
                            if mode == "wrong-thread"
                            else "thread-1",
                            "turn": {
                                "items": [],
                                "id": "wrong" if mode == "wrong-turn" else "turn-1",
                                "status": "failed"
                                if mode == "turn-failed"
                                else "completed",
                            },
                        },
                    }
                )
        elif method == "turn/interrupt":
            send({"id": message["id"], "result": {}})
    if mode == "hang-shutdown":
        time.sleep(60)


if "--version" in sys.argv:
    version = (
        "0.153.0"
        if os.environ.get("WF_RPC_TEST_MODE") == "wrong-version"
        else "0.154.0"
    )
    sys.stdout.write(f"codex-cli {version}\n")
    raise SystemExit(0)
if "app-server" in sys.argv:
    run_turn_server()
    raise SystemExit(0)


mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    response = {
        "id": message["id"],
        "result": {
            "userAgent": "codex-cli/0.154.0",
            "codexHome": str(Path.cwd()),
            "platformFamily": "unix",
            "platformOs": "linux",
        },
    }
    if mode in ("tool", "approval"):
        method = (
            "item/tool/call" if mode == "tool" else "item/permissions/requestApproval"
        )
        sys.stdout.write(
            json.dumps(
                {
                    "id": "server-1",
                    "method": method,
                    "params": (
                        {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "callId": "call-1",
                            "tool": "disabled",
                            "arguments": {"untrusted": "never execute"},
                        }
                        if mode == "tool"
                        else {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "itemId": "item-1",
                            "cwd": str(Path.cwd()),
                            "startedAtMs": 0,
                            "permissions": {},
                        }
                    ),
                }
            )
            + "\n"
        )
        sys.stdout.flush()
        denial = json.loads(sys.stdin.readline())
        response["result"]["denial"] = denial
        sys.stdout.write(json.dumps(response) + "\n")
    elif mode == "hang":
        time.sleep(60)
    elif mode == "oversize":
        sys.stdout.write("x" * 262145)
    elif mode == "invalid":
        sys.stdout.write("not json\n")
    elif mode == "unknown":
        sys.stdout.write(
            json.dumps({"method": "unknown/permission", "params": {}}) + "\n"
        )
    elif mode == "wrong-id":
        response["id"] = 999
        sys.stdout.write(json.dumps(response) + "\n")
    elif mode == "partial-eof":
        sys.stdout.write('{"id":')
        sys.stdout.flush()
        break
    elif mode == "duplicate":
        sys.stdout.write((json.dumps(response) + "\n") * 2)
    else:
        sys.stderr.write("not a protocol frame\n")
        sys.stderr.flush()
        data = json.dumps(response) + "\n"
        for fragment in (data[:7], data[7:]):
            sys.stdout.write(fragment)
            sys.stdout.flush()
    sys.stdout.flush()
