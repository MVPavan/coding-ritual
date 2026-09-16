"""Bounded fake of exercised codex-cli 0.154.0 stdio messages; no model calls."""

import json
import sys
import time
from pathlib import Path

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
