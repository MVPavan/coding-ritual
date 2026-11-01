"""`playbooks/eval/run.sh`, run for real in its boundary with a stub `claude`."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/mvp-mode/playbooks/eval/run.sh"
)
BASH = shutil.which("bash") or "/bin/bash"
# Attempts each thing for real and writes what happened into the copy.
STUB = """#!/usr/bin/env bash
cat > stdin.txt
printf '%s\\n' "$@" > argv.txt
pwd > pwd.txt
env > env.txt
ls -l /proc/$$/fd > fds.txt
command -v helper > helper.txt
cat @WORK@/outside.txt > read-outside.txt 2>&1
{ echo written >> @WORK@/outside.txt; } 2> write-outside.txt
{ echo written >> via-link; } 2> write-link.txt
ls @WORK@/runs > saw-runs.txt 2>&1
ls @WORK@/logs > saw-logs.txt 2>&1
ls -A .. > saw-parent.txt
awk 'BEGIN { print "awk-ran" }' > awk.txt 2>&1

printf '#!/bin/sh\\ntouch @WORK@/hostile-ran-on-host\\ntouch ran-in-boundary\\n' > .git/hostile
chmod +x .git/hostile
git config core.fsmonitor .git/hostile
echo committed-line >> tracked.txt
git add tracked.txt
git -c user.name=t -c user.email=t@t -c core.fsmonitor=false commit -qm own
echo a-new-file-sentence > brand-new

printf 'tracked.txt filter=hide\\n' > .gitattributes
git config filter.hide.clean 'cat > /dev/null'
printf '#!/bin/sh\\necho FAKE-OUTPUT\\n' > .git/fake-diff
chmod +x .git/fake-diff
git config diff.external "$PWD/.git/fake-diff"
echo marked-line >> tracked.txt

[ -z "${STUB_DROP_GIT:-}" ] || rm -rf .git
[ -z "${STUB_HIDE:-}" ] || chmod 000 tracked.txt

sleep "${STUB_SLEEP:-0}"
echo '{"type":"result","subtype":"success"}'
exit "${STUB_EXIT:-0}"
"""

# Tries every way out, and says what happened.
NET_STUB = r"""#!/usr/bin/env bash
cat > stdin.txt
cat /proc/self/mountinfo > mountinfo.txt
cat /proc/net/unix > unix.txt
cat /proc/net/route > route.txt
if [ -n "${HOST_PORT:-}" ]; then
  (exec 8<>"/dev/tcp/127.0.0.1/$HOST_PORT") 2>/dev/null
  echo $? > dev-tcp.txt
  curl -s --max-time 2 "http://127.0.0.1:$HOST_PORT/" >/dev/null 2>&1
  echo $? > curl.txt
  python3 -I -c '
import socket, sys
s = socket.socket(socket.AF_UNIX)
try:
    s.connect("\0" + sys.argv[1])
    print("connected")
except OSError as error:
    print(type(error).__name__)
' "$HOST_ABSTRACT" > abstract.txt 2>&1
fi
exec 7<>/dev/tcp/127.0.0.1/3128
printf 'CONNECT example.invalid:443 HTTP/1.1\r\n\r\n' >&7
head -1 <&7 > denied.txt
exec 7<&-
{ [ -e /etc/resolv.conf ] || [ -e /etc/nsswitch.conf ] && echo present || echo absent; } > etc.txt
cat /etc/hosts > hosts.txt
id -un > whoami.txt
python3 -I -c '
import socket, threading
server = socket.create_server(("localhost", 0))
threading.Thread(target=lambda: server.accept()[0].sendall(b"served\n"), daemon=True).start()
with socket.create_connection(("localhost", server.getsockname()[1])) as client:
    print(client.recv(10).decode().strip())
' > local-server.txt 2>&1
python3 -I -c '
import ctypes, errno, socket
def attempt(family):
    try:
        socket.socket(family, socket.SOCK_STREAM).close()
        return "ok"
    except OSError as error:
        return errno.errorcode[error.errno]
print(attempt(40), attempt(socket.AF_UNIX), attempt(socket.AF_INET))
libc = ctypes.CDLL(None, use_errno=True)
print(libc.syscall(425, 1, None), errno.errorcode[ctypes.get_errno()])
' > families.txt 2>&1
: > probes-done.txt
sleep "${STUB_SLEEP:-0}"
echo '{"type":"result","subtype":"success"}'
exit "${STUB_EXIT:-0}"
"""


@pytest.fixture
def work() -> Iterator[Path]:
    # Not pytest's tmp_path: its name holds "test", which --path-prepend refuses.
    root = Path(tempfile.mkdtemp(prefix="work"))
    (root / "outside.txt").write_text("host secret\n")
    template = root / "template"
    template.mkdir()
    (template / "tracked.txt").write_text("base\n")
    (template / "via-link").symlink_to(root / "outside.txt")
    for args in (
        ["init", "-q"],
        ["add", "tracked.txt", "via-link"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"],
    ):
        subprocess.run(["git", "-C", str(template), *args], check=True)
    # Like the native CLI, a symlink out of its own directory.
    native = root / "versions" / "1.0"
    native.parent.mkdir()
    native.write_text(STUB.replace("@WORK@", str(root)))
    native.chmod(0o755)
    (root / "bin").mkdir()
    (root / "bin" / "claude").symlink_to(native)
    tools = root / "tools"
    tools.mkdir()
    (tools / "helper").write_text("#!/bin/sh\n")
    (tools / "helper").chmod(0o755)
    (root / "prompt.txt").write_text("Please fix the crash.\n\n")
    yield root
    shutil.rmtree(root)


@pytest.fixture
def boundary() -> None:
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        pytest.skip("bwrap is not on PATH")
    probe = subprocess.run(
        [bwrap, "--unshare-all", "--ro-bind", "/", "/", "/usr/bin/true"],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        pytest.skip(f"bwrap cannot start: {probe.stderr.strip()}")


def _env(work: Path, **extra: str) -> dict[str, str]:
    return {
        **os.environ,
        "PATH": f"{work / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "AUTH_VALUE": "not-a-real-token",
        "CLAUDE_CODE_SIMPLE": "1",
        **extra,
    }


def _argv(work: Path, run_id: str, *extra: str) -> list[str]:
    return [
        BASH, str(SCRIPT),
        "--template", str(work / "template"),
        "--runs", str(work / "runs"),
        "--logs", str(work / "logs"),
        "--id", run_id,
        "--prompt", str(work / "prompt.txt"),
        "--model", "some-model",
        "--permission-mode", "default",
        "--max-turns", "7",
        *extra,
    ]  # fmt: skip


def _run(
    work: Path, run_id: str, env: dict[str, str], *extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _argv(work, run_id, "--auth-env", "AUTH_VALUE", *extra),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.usefixtures("boundary")
def test_the_candidate_sees_only_its_copy(work: Path) -> None:
    first = _run(work, "first", _env(work))
    assert first.returncode == 0, first.stderr
    result = _run(work, "second", _env(work))
    assert result.returncode == 0, result.stderr
    assert "exit=0 second" in result.stdout
    copy = work / "runs" / "second"

    assert (copy / "pwd.txt").read_text().strip() == "/home/user/project"
    assert "host secret" not in (copy / "read-outside.txt").read_text()
    assert (work / "outside.txt").read_text() == "host secret\n"
    assert (copy / "write-outside.txt").read_text()
    assert (copy / "write-link.txt").read_text()
    assert "first" not in (copy / "saw-runs.txt").read_text()
    assert "second" not in (copy / "saw-logs.txt").read_text()
    assert (copy / "saw-parent.txt").read_text().strip() == "project"
    assert (copy / "awk.txt").read_text().strip() == "awk-ran"
    descriptors = (copy / "fds.txt").read_text()
    assert str(work) not in descriptors
    assert "/dev/null" not in descriptors  # stderr reaches the log
    assert "filter" not in descriptors


@pytest.mark.usefixtures("boundary")
def test_only_the_chosen_environment_arrives(work: Path) -> None:
    env = _env(work, **{"not.a.name": "1", "BASH_FUNC_x%%": "() { :; }"})
    result = _run(work, "r", env, "--path-prepend", str(work / "tools"))
    assert result.returncode == 0, result.stderr
    copy = work / "runs" / "r"

    lines = (copy / "env.txt").read_text().splitlines()
    seen = dict(line.split("=", 1) for line in lines)
    assert seen["AUTH_VALUE"] == "not-a-real-token"
    assert seen["HOME"] == "/home/user"
    assert seen["DISABLE_AUTOUPDATER"] == "1"
    # PWD, SHLVL and _ are the stub's own shell.
    assert set(seen) == {
        "AUTH_VALUE", "DISABLE_AUTOUPDATER", "HOME", "HTTPS_PROXY", "LANG", "PATH",
        "PWD", "SHLVL", "_", "https_proxy",
    }  # fmt: skip
    assert seen["HTTPS_PROXY"] == seen["https_proxy"] == "http://127.0.0.1:3128"
    assert seen["PATH"].startswith(f"{work / 'tools'}:")
    assert (copy / "helper.txt").read_text().strip() == str(work / "tools" / "helper")


@pytest.mark.usefixtures("boundary")
def test_prompt_arrives_on_stdin_and_flags_are_passed(work: Path) -> None:
    prompt = "- a bullet first\nthen more\n\n"
    (work / "prompt.txt").write_text(prompt)
    assert _run(work, "r", _env(work)).returncode == 0
    copy = work / "runs" / "r"

    assert (copy / "stdin.txt").read_text() == prompt
    args = (copy / "argv.txt").read_text().splitlines()
    assert args[0] == "-p"
    assert "a bullet" not in " ".join(args)
    flags = " ".join(args)
    for expected in (
        "--model some-model",
        "--setting-sources project",
        "--strict-mcp-config",
        "--permission-mode default",
        "--max-turns 7",
        "--no-session-persistence",
        "--output-format stream-json",
        "--verbose",
    ):
        assert expected in flags
    log = work / "logs" / "r.jsonl"
    assert json.loads(log.read_text())["subtype"] == "success"


@pytest.mark.usefixtures("boundary")
def test_the_diff_is_the_files_whatever_the_copys_git_says(work: Path) -> None:
    assert _run(work, "r", _env(work)).returncode == 0

    diff = (work / "logs" / "r.diff").read_text()
    assert "+marked-line" in diff  # past a clean filter that hides it from Git
    assert "FAKE-OUTPUT" not in diff  # the candidate's diff program never ran
    assert "+a-new-file-sentence" in diff  # a new file's contents
    assert "+committed-line" in diff  # a commit the candidate made
    assert "diff capture failed" not in diff
    assert not (work / "hostile-ran-on-host").exists()
    assert (work / "template" / "tracked.txt").read_text() == "base\n"


@pytest.mark.usefixtures("boundary")
def test_a_deleted_git_still_gets_a_diff_and_keeps_the_exit_code(work: Path) -> None:
    env = _env(work, STUB_DROP_GIT="1", STUB_EXIT="5")
    argv = ("--auth-env", "STUB_DROP_GIT", "--auth-env", "STUB_EXIT")
    assert _run(work, "r", env, *argv).returncode == 5

    diff = (work / "logs" / "r.diff").read_text()
    assert "+marked-line" in diff
    assert "diff capture failed" not in diff


@pytest.mark.usefixtures("boundary")
def test_a_failed_capture_is_recorded_and_keeps_the_exit_code(work: Path) -> None:
    env = _env(work, STUB_HIDE="1", STUB_EXIT="5")
    argv = ("--auth-env", "STUB_HIDE", "--auth-env", "STUB_EXIT")
    assert _run(work, "r", env, *argv).returncode == 5

    assert "diff capture failed: exit=2" in (work / "logs" / "r.diff").read_text()


@pytest.mark.usefixtures("boundary")
def test_session_exit_code_is_returned(work: Path) -> None:
    result = _run(work, "bad", _env(work, STUB_EXIT="3"), "--auth-env", "STUB_EXIT")
    assert result.returncode == 3
    assert "exit=3 bad" in result.stdout


@pytest.mark.usefixtures("boundary")
def test_concurrent_launches_with_one_id_run_once(work: Path) -> None:
    env = _env(work, STUB_SLEEP="1")
    argv = _argv(work, "same", "--auth-env", "AUTH_VALUE", "--auth-env", "STUB_SLEEP")
    launches = [
        subprocess.Popen(argv, env=env, stderr=subprocess.DEVNULL) for _ in range(2)
    ]
    codes = sorted(launch.wait() for launch in launches)

    assert codes == [0, 2]
    log = (work / "logs" / "same.jsonl").read_text().splitlines()
    assert [json.loads(line)["subtype"] for line in log] == ["success"]


@pytest.mark.usefixtures("boundary")
def test_an_existing_run_is_never_overwritten(work: Path) -> None:
    assert _run(work, "again", _env(work)).returncode == 0
    log = work / "logs" / "again.jsonl"
    before = log.read_text()

    assert _run(work, "again", _env(work)).returncode == 2
    assert log.read_text() == before


def _use_net_stub(work: Path) -> None:
    (work / "versions" / "1.0").write_text(NET_STUB)


def _proxy_dir(copy: Path) -> Path:
    """The private directory, named by the mount the stub saw and proxied through."""
    found = re.search(r"proxy\.\w{8}", (copy / "mountinfo.txt").read_text())
    assert found is not None
    return Path("/tmp") / found.group()


def _still_running(word: str) -> bool:
    for cmdline in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            if word.encode() in cmdline.read_bytes():
                return True
        except OSError:
            pass
    return False


def _proxy_is_gone(private: Path) -> bool:
    return not private.exists() and not _still_running(private.name)


@pytest.mark.usefixtures("boundary")
def test_the_only_way_out_is_the_proxy(work: Path) -> None:
    _use_net_stub(work)
    hits: list[socket.socket] = []
    listener = socket.create_server(("127.0.0.1", 0))
    listener.settimeout(0.1)
    abstract = socket.socket(socket.AF_UNIX)
    name = f"host-only-{os.getpid()}"
    abstract.bind(f"\0{name}")
    abstract.listen()

    stop = threading.Event()

    def watch() -> None:
        while not stop.is_set():
            try:
                hits.append(listener.accept()[0])
            except TimeoutError:
                pass

    watcher = threading.Thread(target=watch)
    watcher.start()
    env = _env(work, HOST_PORT=str(listener.getsockname()[1]), HOST_ABSTRACT=name)
    try:
        result = _run(
            work, "r", env, "--auth-env", "HOST_PORT", "--auth-env", "HOST_ABSTRACT"
        )
    finally:
        stop.set()
        watcher.join()
    assert result.returncode == 0, result.stderr
    copy = work / "runs" / "r"

    assert hits == []
    assert (copy / "dev-tcp.txt").read_text().strip() != "0"
    assert (copy / "curl.txt").read_text().strip() != "0"
    assert name not in (copy / "unix.txt").read_text()
    assert "ConnectionRefused" in (copy / "abstract.txt").read_text()
    listener.close()
    abstract.close()

    # The forwarder listens, and its proxy refuses what is not allowed and logs it.
    assert (copy / "denied.txt").read_text().startswith("HTTP/1.1 403")
    egress_log = (work / "logs" / "r.egress").read_text()
    assert "deny example.invalid:443" in egress_log
    assert "allow" not in egress_log

    # No route out, none of the host's network files, and a localhost of its own.
    assert (copy / "route.txt").read_text().splitlines()[1:] == []
    assert (copy / "etc.txt").read_text().strip() == "absent"
    assert (copy / "hosts.txt").read_text().strip() == "127.0.0.1 localhost"
    assert (copy / "whoami.txt").read_text().strip() == "user"
    assert (copy / "local-server.txt").read_text().strip() == "served"

    # The filter: AF_VSOCK crosses a namespace, and io_uring can make a socket.
    assert (copy / "families.txt").read_text().splitlines() == [
        "EAFNOSUPPORT ok ok",
        "-1 ENOSYS",
    ]

    # The mount table holds no word that reveals the experiment.
    mounts = (copy / "mountinfo.txt").read_text()
    assert str(SCRIPT.parent) not in mounts
    assert "/opt/cli/egress.py" in mounts
    assert "/filter" not in mounts


@pytest.mark.usefixtures("boundary")
def test_the_diffs_boundary_gets_no_proxy(work: Path) -> None:
    fake = work / "bin" / "bwrap"
    real = shutil.which("bwrap")
    assert real is not None
    fake.write_text(
        f'#!/bin/sh\nprintf "%s\\0" "$*" >> {work}/calls.txt\nexec {real} "$@"\n'
    )
    fake.chmod(0o755)

    assert _run(work, "r", _env(work)).returncode == 0

    probe, session, capture = (work / "calls.txt").read_text().rstrip("\0").split("\0")
    assert "--share-net" not in probe + session + capture
    assert "/run/proxy.sock" in session
    assert "/run/proxy.sock" not in capture
    assert "HTTPS_PROXY" not in capture
    assert "--seccomp 6" in session
    assert "--seccomp 6" in capture
    for gone in ("resolv.conf", "nsswitch.conf"):
        assert gone not in session


@pytest.mark.usefixtures("boundary")
@pytest.mark.parametrize(
    ("extra_env", "extra_args", "expected"),
    [
        ({}, (), 0),
        ({"STUB_EXIT": "3"}, ("--auth-env", "STUB_EXIT"), 3),
        ({"STUB_SLEEP": "60"}, ("--auth-env", "STUB_SLEEP", "--timeout", "1"), 124),
    ],
    ids=["normal", "failed-session", "timeout"],
)
def test_the_proxy_never_outlives_the_run(
    work: Path, extra_env: dict[str, str], extra_args: tuple[str, ...], expected: int
) -> None:
    _use_net_stub(work)
    assert _run(work, "r", _env(work, **extra_env), *extra_args).returncode == expected
    assert _proxy_is_gone(_proxy_dir(work / "runs" / "r"))


def _sleeping_session(work: Path) -> subprocess.Popen[bytes]:
    """A run whose stub has finished its probes and is sleeping."""
    _use_net_stub(work)
    argv = _argv(work, "r", "--auth-env", "AUTH_VALUE", "--auth-env", "STUB_SLEEP")
    run = subprocess.Popen(
        argv,
        env=_env(work, STUB_SLEEP="60"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 15
    while not (work / "runs" / "r" / "probes-done.txt").exists():
        assert time.monotonic() < deadline, "the stub never finished its probes"
        time.sleep(0.05)
    return run


@pytest.mark.usefixtures("boundary")
@pytest.mark.parametrize(
    ("signal_number", "expected"), [(signal.SIGINT, 130), (signal.SIGTERM, 143)]
)
def test_an_interrupt_ends_the_session_and_the_proxy_now(
    work: Path, signal_number: signal.Signals, expected: int
) -> None:
    run = _sleeping_session(work)

    run.send_signal(signal_number)

    assert run.wait(timeout=10) == expected
    assert _proxy_is_gone(_proxy_dir(work / "runs" / "r"))


@pytest.mark.usefixtures("boundary")
def test_an_interrupt_stops_a_slow_diff_now(work: Path) -> None:
    (work / "versions" / "1.0").write_text("#!/bin/sh\ncat >/dev/null\n")
    # Sparse: equal, so diff reads all of it, and it takes no disk.
    with (work / "template" / "big").open("wb") as big:
        big.truncate(256 * 1024**3)
    real = shutil.which("bwrap")
    assert real is not None
    marker = work / "in-diff"
    fake = work / "bin" / "bwrap"
    fake.write_text(
        f'#!/bin/bash\n[[ "$*" != *usr/bin/diff* ]] || touch {marker}\nexec {real} "$@"\n'
    )
    fake.chmod(0o755)
    argv = _argv(work, "r", "--auth-env", "AUTH_VALUE", "--timeout", "60")
    run = subprocess.Popen(
        argv, env=_env(work), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    deadline = time.monotonic() + 15
    while not marker.exists():
        assert time.monotonic() < deadline, "the diff never started"
        time.sleep(0.05)
    time.sleep(0.2)

    run.send_signal(signal.SIGTERM)

    assert run.wait(timeout=5) == 143
    deadline = time.monotonic() + 5
    while _still_running(str(work / "runs" / "r")):
        assert time.monotonic() < deadline, "the diff outlived the signal"
        time.sleep(0.05)


@pytest.mark.usefixtures("boundary")
def test_a_stale_pid_that_is_not_timeout_is_not_signalled(work: Path) -> None:
    run = _sleeping_session(work)
    recorded = _proxy_dir(work / "runs" / "r") / "session"
    session = int(recorded.read_text())
    bystander = subprocess.Popen(["sleep", "60"])
    recorded.write_text(f"{bystander.pid}\n")

    run.send_signal(signal.SIGTERM)

    try:
        assert run.wait(timeout=10) == 143
        assert bystander.poll() is None
    finally:
        bystander.kill()
        bystander.wait()
        os.kill(session, signal.SIGTERM)


def test_a_filter_that_cannot_be_written_stops_the_launch(work: Path) -> None:
    beside = work / "beside"
    beside.mkdir()
    shutil.copy(SCRIPT, beside / "run.sh")
    (beside / "egress.py").write_text("raise SystemExit(1)\n")
    argv = _argv(work, "r", "--auth-env", "AUTH_VALUE")
    argv[1] = str(beside / "run.sh")

    result = subprocess.run(
        argv, env=_env(work), capture_output=True, text=True, check=False
    )

    assert result.returncode == 2
    assert "seccomp filter" in result.stderr
    assert not (work / "runs" / "r").exists()


def test_auth_env_is_required_and_must_have_a_value(work: Path) -> None:
    missing = subprocess.run(
        _argv(work, "r"), env=_env(work), capture_output=True, text=True, check=False
    )
    assert missing.returncode == 2
    assert "--auth-env" in missing.stderr

    empty = _run(work, "r", _env(work, AUTH_VALUE=""))
    assert empty.returncode == 2
    assert "AUTH_VALUE" in empty.stderr
    assert not (work / "runs").exists()


def test_no_bwrap_refuses(work: Path) -> None:
    only = work / "only"
    only.mkdir()
    grep = shutil.which("grep")
    assert grep is not None
    (only / "grep").symlink_to(grep)
    env = {**_env(work), "PATH": f"{only}{os.pathsep}{work / 'bin'}"}

    result = _run(work, "r", env)

    assert result.returncode == 2
    assert "bwrap is required" in result.stderr
    assert not (work / "runs").exists()


def test_a_bwrap_that_cannot_start_refuses(work: Path) -> None:
    (work / "bin" / "bwrap").write_text("#!/bin/sh\necho denied >&2\nexit 1\n")
    (work / "bin" / "bwrap").chmod(0o755)

    result = _run(work, "r", _env(work))

    assert result.returncode == 2
    assert "bwrap cannot start: denied" in result.stderr
    assert not (work / "runs" / "r").exists()


@pytest.mark.usefixtures("boundary")
def test_revealing_or_unsafe_paths_are_refused(work: Path) -> None:
    revealing = work / "benchmark"
    revealing.mkdir()
    result = _run(work, "r", _env(work), "--path-prepend", str(revealing))
    assert result.returncode == 2
    assert "reveals the experiment" in result.stderr

    named = _run(work, "benchmark-1", _env(work))
    assert named.returncode == 2
    assert "reveals the experiment" in named.stderr
    assert not (work / "runs" / "benchmark-1").exists()

    assert _run(work, "../escape", _env(work)).returncode == 2
