"""statechart.py install over a temporary home: every download checked (pins,
signatures, catalog) before anything changes, existing targets reused or
refused and never overwritten, and only what the run created removed, on
failure and on removal. The publishers and mise are faked; gpg is the real
one, with throwaway keys standing in for the publishers' keys."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True  # no bytecode beside the shipped scripts
sys.path.insert(0, str(ROOT / ".claude/skills/statechart/scripts"))

from statechart_lib import install

GPG = shutil.which("gpg")
pytestmark = [
    pytest.mark.skipif(GPG is None, reason="install checks signatures with gpg"),
    pytest.mark.skipif(
        sys.platform != "linux" or os.uname().machine != "x86_64",
        reason="the pins are for Linux x86-64",
    ),
]


@dataclass
class Keys:
    home: str
    good: str
    other: str

    def gpg(self, *args: str) -> bytes:
        command = [str(GPG), "--batch", "--homedir", self.home, "--pinentry-mode"]
        return subprocess.run(
            [*command, "loopback", "--passphrase", "", *args],
            check=True,
            capture_output=True,
        ).stdout


@pytest.fixture(scope="module")
def keys() -> Iterator[Keys]:
    home = tempfile.mkdtemp(prefix="sc-gpg-")  # short: gpg-agent's socket path
    made = Keys(home, "", "")
    for name in ("good", "other"):
        made.gpg("--quick-gen-key", f"{name} <{name}@example.invalid>", "ed25519")
        listed = made.gpg("--with-colons", "--list-keys", f"{name}@example.invalid")
        fpr = next(x for x in listed.decode().splitlines() if x.startswith("fpr:"))
        setattr(made, name, fpr.split(":")[9])
    yield made
    for step in ("--kill", "all"), ("--remove-socketdir",):
        subprocess.run(["gpgconf", "--homedir", home, *step], check=False)
    shutil.rmtree(home, ignore_errors=True)


def _sha(data: bytes, name: str = "sha256") -> str:
    return hashlib.new(name, data).hexdigest()


def _archive() -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        for name, data in (("bin/java", b"java"), ("lib/modules", b"modules")):
            info = tarfile.TarInfo(f"jdk-25.0.5+8/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return out.getvalue()


@pytest.fixture
def served(
    keys: Keys, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> dict[str, bytes]:
    """What the fake publishers serve by URL, with the pins set to match it."""
    monkeypatch.delenv("JAVA", raising=False)
    monkeypatch.delenv("TLA2TOOLS", raising=False)
    mise, jar, archive = b"#!/bin/sh\n", b"jar", _archive()
    sums = f"{'0' * 64}  ./other\n{_sha(mise)}  ./{install.MISE_ASSET}\n".encode()
    (tmp_path / "sums").write_bytes(sums)
    (tmp_path / "archive").write_bytes(archive)
    good = ["--local-user", keys.good, "--output", "-"]
    entry = {"vendor": "temurin", "version": install.JAVA_PIN.split("-", 1)[1],
             "image_type": "jdk", "features": [], "url": install.JAVA_URL,
             "checksum": f"sha256:{_sha(archive)}"}  # fmt: skip
    musl = dict(entry, features=["musl"], url="elsewhere")
    for name, value in (("MISE_SHA256", _sha(mise)), ("MISE_SUMS_SHA256", _sha(sums)),
                        ("JAVA_SHA256", _sha(archive)), ("TLC_SHA256", _sha(jar)),
                        ("TLC_SHA1", _sha(jar, "sha1")), ("MISE_KEY", keys.good),
                        ("JAVA_KEY", keys.good)):  # fmt: skip
        monkeypatch.setattr(install, name, value)
    public = keys.gpg("--armor", "--export", keys.good)
    return {
        install.MISE_URL: mise,
        f"{install.MISE_BASE}/SHASUMS256.txt": sums,
        f"{install.MISE_BASE}/SHASUMS256.asc": keys.gpg(
            *good, "--clearsign", str(tmp_path / "sums")
        ),
        install.MISE_KEY_URL: public,
        install.CATALOG_URL: json.dumps([musl, entry]).encode(),
        install.JAVA_URL: archive,
        install.JAVA_URL + ".sig": keys.gpg(
            *good, "--detach-sign", str(tmp_path / "archive")
        ),
        install.JAVA_KEY_URL: public,
        install.TLC_URL: jar,
    }


@dataclass
class Fake:
    """The publishers (fetch) and mise and java (run) over a temporary home."""

    home: Path
    served: dict[str, bytes]
    fetched: list[str] = field(default_factory=list)
    ran: list[str] = field(default_factory=list)
    tamper_tree: bool = False
    banner: str = install.TLC_BANNER

    def fetch(self, url: str, target: Path) -> None:
        assert not self.ran, "a download after mise or java ran"
        self.fetched.append(url)
        target.write_bytes(self.served[url])

    def run(self, command: list[str]) -> str:
        java = install.java_path(self.home).parents[1]
        if command[0].endswith("/bin/java"):
            self.ran.append("java")
            return f"TLC2 {self.banner}"
        self.ran.append(command[1])
        if command[1] == "install":  # as mise does: tree, aliases, cache
            with tarfile.open(fileobj=io.BytesIO(self.served[install.JAVA_URL])) as t:
                t.extractall(java.parent / "x", filter="tar")
            (java.parent / "x/jdk-25.0.5+8").rename(java)
            shutil.rmtree(java.parent / "x")
            (java.parent / "temurin-25").symlink_to(f"./{install.JAVA_PIN}")
            (self.home / ".cache/mise").mkdir(parents=True, exist_ok=True)
            (self.home / ".cache/mise/download.tgz").write_bytes(b"cache")
            if self.tamper_tree:
                (java / "bin/java").write_bytes(b"other")
        if command[1] == "uninstall":
            shutil.rmtree(java)
        return {
            "--version": f"{install.MISE_VERSION} linux-x64 (2026-10-30)",
            "ls-remote": f"temurin-21\n{install.JAVA_PIN}\n",
            "where": f"{java}\n",
        }.get(command[1], "")

    def install(self) -> list[str]:
        return install.install(self.home, fetch=self.fetch, run=self.run)


def _tree(home: Path) -> dict[str, bytes | str]:
    """Every path under home with its content, link target or folder mark."""
    found: dict[str, bytes | str] = {}
    for path in sorted(home.rglob("*")):
        key = str(path.relative_to(home))
        found[key] = (
            f"-> {os.readlink(path)}" if path.is_symlink()
            else path.read_bytes() if path.is_file() else "dir"
        )  # fmt: skip
    return found


def _without_records(tree: dict[str, bytes | str]) -> dict[str, bytes | str]:
    return {k: v for k, v in tree.items() if not k.startswith(".local/state")}


def _personal(home: Path) -> None:
    """Files the person already has beside the targets."""
    for name in (".local/bin/other", ".cache/mise/keep", ".local/share/mise/k"):
        (home / name).parent.mkdir(parents=True, exist_ok=True)
        (home / name).write_bytes(b"theirs")


def test_install_runs_every_check_then_removes_only_its_own(
    served: dict[str, bytes], tmp_path: Path
) -> None:
    home = tmp_path / "home"
    _personal(home)
    before = _tree(home)
    fake = Fake(home, served)
    done = fake.install()
    assert fake.fetched == list(served)  # all fetched, in order, before any run
    assert fake.ran == ["--version", "ls-remote", "install", "where", "java"]
    mise, jar = home / ".local/bin/mise", install.jar_path(home)
    assert mise.read_bytes() == served[install.MISE_URL]
    assert (mise.stat().st_mode & 0o777, jar.stat().st_mode & 0o777) == (0o755, 0o644)
    assert jar.read_bytes() == served[install.TLC_URL]
    assert install.java_path(home).read_bytes() == b"java"
    folder = Path(done[-1].split()[1])
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["status"] == "installed" and manifest["reused"] == []
    assert f"ABSENT {mise}" in (folder / "inventory-before.txt").read_text()
    assert f" {jar}\n" in (folder / "inventory-after.txt").read_text()

    jar.chmod(0o600)  # a mode change leaves the content, so the jar still goes
    lines = install.remove(folder, run=fake.run)
    assert fake.ran[-1] == "uninstall" and lines == [lines[0]]
    assert _without_records(_tree(home)) == _without_records(before)
    assert (folder / "inventory-after-removal.txt").is_file()


def test_removal_keeps_what_changed_since_the_install(
    served: dict[str, bytes], tmp_path: Path
) -> None:
    home = tmp_path / "home"
    fake = Fake(home, served)
    folder = Path(fake.install()[-1].split()[1])
    install.jar_path(home).write_bytes(b"edited")
    installs = install.java_path(home).parents[2]
    (installs / "notes").write_bytes(b"theirs")
    lines = install.remove(folder, run=fake.run)
    kept = [str(install.jar_path(home)), str(installs)]
    assert [line.split()[-1] for line in lines[1:]] == kept
    assert install.jar_path(home).read_bytes() == b"edited"
    assert (installs / "notes").is_file() and not (home / ".local/bin/mise").exists()


def test_material_added_inside_java_stays_and_java_is_not_uninstalled(
    served: dict[str, bytes], tmp_path: Path
) -> None:
    home = tmp_path / "home"
    fake = Fake(home, served)
    folder = Path(fake.install()[-1].split()[1])
    java = install.java_path(home).parents[1]
    (java / "my-notes.txt").write_bytes(b"theirs")
    lines = install.remove(folder, run=fake.run)
    assert "uninstall" not in fake.ran
    assert (java / "my-notes.txt").read_bytes() == b"theirs"
    assert install.java_path(home).read_bytes() == b"java"
    assert any(line.endswith(str(java / "my-notes.txt")) for line in lines)


def test_a_stale_record_removes_and_runs_nothing_after_a_replacement(
    served: dict[str, bytes], tmp_path: Path
) -> None:
    home = tmp_path / "home"
    fake = Fake(home, served)
    folder = Path(fake.install()[-1].split()[1])
    install.remove(folder, run=fake.run)
    mise, jar = home / ".local/bin/mise", install.jar_path(home)
    for path, data in (
        (install.java_path(home), b"java"),  # equal to what the record names
        (mise, served[install.MISE_URL]),
        (jar, served[install.TLC_URL]),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    after = _tree(home)
    ran = list(fake.ran)
    install.remove(folder, run=fake.run)
    assert fake.ran == ran  # the replacement mise never runs
    assert _without_records(_tree(home)) == _without_records(after)


@pytest.mark.parametrize("where", ["tree", "banner"])
def test_a_failure_midway_removes_only_what_the_run_created(
    served: dict[str, bytes], tmp_path: Path, where: str
) -> None:
    home = tmp_path / "home"
    _personal(home)
    before = _tree(home)
    fake = Fake(home, served, tamper_tree=where == "tree", banner="no banner")
    with pytest.raises(install.InstallError, match="removed what this run created"):
        fake.install()
    assert "uninstall" in fake.ran
    assert _without_records(_tree(home)) == _without_records(before)
    (folder,) = (home / install.RECORDS).iterdir()
    assert json.loads((folder / "manifest.json").read_text())["status"].startswith(
        "failed"
    )
    assert (
        f" {home / '.cache/mise/keep'}\n"
        in (folder / "inventory-after.txt").read_text()
    )


def _tamper(served: dict[str, bytes], url: str, keys: Keys) -> None:
    if url.endswith(".asc"):  # the signed text, not the signature
        served[url] = served[url].replace(b"0000", b"1111", 1)
    elif url.endswith(".sig"):
        served[url] = keys.gpg("--local-user", keys.good, "--detach-sign", "--output",
                               "-", str(ROOT / "pyproject.toml"))  # fmt: skip
    elif url.endswith("x86_64.json"):
        served[url] = served[url].replace(b"sha256:", b"sha256:0")
    elif "key" in url or "pks" in url:  # another key than the pinned one
        served[url] = keys.gpg("--armor", "--export", keys.other)
    else:
        served[url] += b"!"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        (install.MISE_URL, "is not the pinned"),
        (f"{install.MISE_BASE}/SHASUMS256.txt", "is not the pinned"),
        (f"{install.MISE_BASE}/SHASUMS256.asc", "SHASUMS256.asc: no good signature"),
        (install.MISE_KEY_URL, "mise-key.asc is not"),
        (install.CATALOG_URL, "catalog does not name"),
        (install.JAVA_URL, "is not the pinned"),
        (install.JAVA_URL + ".sig", f"{install.JAVA_ARCHIVE}: no good signature"),
        (install.JAVA_KEY_URL, "java-key.asc is not"),
        (install.TLC_URL, "is not the pinned"),
    ],
)
def test_a_failed_check_stops_before_anything_changes(
    served: dict[str, bytes], keys: Keys, tmp_path: Path, url: str, message: str
) -> None:
    home = tmp_path / "home"
    _personal(home)
    before = _tree(home)
    _tamper(served, url, keys)
    fake = Fake(home, served)
    with pytest.raises(install.InstallError, match=message):
        fake.install()
    assert fake.ran == [] and _tree(home) == before


def _conflict(home: Path, what: str) -> Path:
    mise, jar = home / ".local/bin/mise", install.jar_path(home)
    java = install.java_path(home).parents[1]
    target = {"mise": mise, "mise-link": mise, "jar": jar, "java-link": java}[what]
    target.parent.mkdir(parents=True)
    (home / "theirs").write_bytes(b"#!/bin/sh\n")  # the pinned mise's bytes
    if what.endswith("-link"):
        target.symlink_to(home / "theirs")
    else:
        target.write_bytes(b"theirs")
    return target


@pytest.mark.parametrize("what", ["mise", "mise-link", "jar", "java-link"])
def test_an_existing_file_or_symlink_at_a_target_is_refused(
    served: dict[str, bytes], tmp_path: Path, what: str
) -> None:
    home = tmp_path / "home"
    target = _conflict(home, what)
    before = _tree(home)
    fake = Fake(home, served)
    with pytest.raises(
        install.InstallError, match=re.escape(f"{target} is already there as a")
    ):
        fake.install()
    assert fake.fetched == [] and fake.ran == [] and _tree(home) == before


def test_an_existing_java_that_differs_is_left_and_never_uninstalled(
    served: dict[str, bytes], tmp_path: Path
) -> None:
    home = tmp_path / "home"
    java = install.java_path(home)
    java.parent.mkdir(parents=True)
    java.write_bytes(b"their java")
    before = _tree(home)
    fake = Fake(home, served)
    with pytest.raises(install.InstallError, match="did not install it"):
        fake.install()
    assert fake.ran == [] and _tree(home) == before


def test_verified_existing_assets_are_reused_and_never_removed(
    served: dict[str, bytes], tmp_path: Path
) -> None:
    home = tmp_path / "home"
    first = Fake(home, served)
    first.install()
    shutil.rmtree(home / install.RECORDS)
    before = _tree(home)
    again = Fake(home, served)
    done = again.install()
    assert [u for u in again.fetched if u in (install.MISE_URL, install.TLC_URL)] == []
    assert again.ran == ["--version", "java"]
    assert sum("reused" in line for line in done) == 3
    (folder,) = (home / install.RECORDS).iterdir()
    install.remove(folder, run=again.run)
    assert "uninstall" not in again.ran
    assert _without_records(_tree(home)) == _without_records(before)


def test_a_missing_gpg_stops_and_names_the_pointed_install(
    served: dict[str, bytes], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    fake = Fake(tmp_path / "home", served)
    with pytest.raises(install.InstallError, match="gpg .* set JAVA and TLA2TOOLS"):
        fake.install()
    assert fake.fetched == [] and not (tmp_path / "home").exists()
