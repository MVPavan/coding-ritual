"""The per-user install of mise, Java and TLC at pinned versions (install.md).

Every download is checked against its pin, and mise's and Java's also against
their publishers' signatures, before anything in the home folder changes. An
asset already at a target is reused only when it matches its pin; anything else
there is refused, never overwritten. Each change is then written to a manifest
as it happens, so a failure removes exactly what this run created, and
`remove` does the same later. JAVA and TLA2TOOLS point at an existing install
instead, and then nothing is installed."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MISE_VERSION = "2026.10.24"
MISE_BASE = f"https://github.com/jdx/mise/releases/download/v{MISE_VERSION}"
MISE_ASSET = f"mise-v{MISE_VERSION}-linux-x64"
MISE_URL = f"{MISE_BASE}/{MISE_ASSET}"
MISE_SHA256 = "be97dbac1c0b1fe08bd8c0cf01690f4273ea9aa02ad766b98d4e20c43eb9059d"
MISE_SUMS_SHA256 = "587549ac3ecde92294f760bb713dc0d0a3d001b8f74c3660679686bdb47e7a40"
# Signing keys from where each publisher says to get them, pinned by fingerprint:
# mise.jdx.dev/installing-mise.html and adoptium.net/installation/gpg-verification/.
MISE_KEY = "24853EC9F655CE80B48E6C3A8B81C9D17413A06D"
MISE_KEY_URL = f"https://keys.openpgp.org/vks/v1/by-fingerprint/{MISE_KEY}"
JAVA_KEY = "3B04D753C9050D9A5D343F39843C48A565F8F04B"
JAVA_KEY_URL = (
    f"https://keyserver.ubuntu.com/pks/lookup?op=get&options=mr&search=0x{JAVA_KEY}"
)
JAVA_PIN = "temurin-25.0.5+8.0.LTS"
JAVA_ARCHIVE = "OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz"
JAVA_URL = f"https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.5%2B8/{JAVA_ARCHIVE}"
JAVA_SHA256 = "68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb"
CATALOG_URL = "https://mise-java.jdx.dev/jvm/ga/linux/x86_64.json"
TLC_VERSION = "1.7.4"
TLC_URL = (
    f"https://github.com/tlaplus/tlaplus/releases/download/v{TLC_VERSION}/tla2tools.jar"
)
TLC_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
TLC_SHA1 = "bee4a54f3ee3d4afc347c3240ec2d9e93b075104"
TLC_BANNER = "Version 2.19 of 08 August 2024"
# What the inventories list, relative to the home folder; the four mise folders
# are where mise itself writes.
MISE_DIRS = (".local/share/mise", ".local/state/mise", ".cache/mise", ".config/mise")
ROOTS = (".local/bin/mise", ".local/share/tla2tools", *MISE_DIRS)
RECORDS = ".local/state/statechart-install"
POINT = "or set JAVA and TLA2TOOLS to an existing install (install.md)"

Fetch = Callable[[str, Path], None]
Run = Callable[[list[str]], str]
Entry = tuple[str, int, int, str]  # type (f, d, l), size, mtime in ns, link target


class InstallError(Exception):
    """A check failed or a target was refused; see the message for what changed."""


def jar_path(home: Path) -> Path:
    return home / ".local/share/tla2tools" / TLC_VERSION / "tla2tools.jar"


def java_path(home: Path) -> Path:
    return home / ".local/share/mise/installs/java" / JAVA_PIN / "bin/java"


def _fetch(url: str, target: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out)


def _run(command: list[str]) -> str:
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    return done.stdout + done.stderr


def _digest(path: Path, name: str) -> str:
    return hashlib.new(name, path.read_bytes()).hexdigest()


def _pinned(path: Path, name: str, expected: str) -> None:
    found = _digest(path, name)
    if found != expected:
        raise InstallError(
            f"{path.name}: {name} {found} is not the pinned {expected}; stopped"
        )


def _entry(path: Path) -> Entry | None:
    try:
        found = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(found.st_mode):
        return ("l", 0, 0, os.readlink(path))
    if stat.S_ISDIR(found.st_mode):
        return ("d", 0, 0, "")
    return ("f", found.st_size, found.st_mtime_ns, "")


def _snapshot(home: Path) -> dict[str, Entry]:
    """Every entry under ROOTS, with the folders leading to them."""
    found: dict[str, Entry] = {}
    for root in ROOTS:
        parts = Path(root).parts
        for depth in range(1, len(parts) + 1):
            path = home.joinpath(*parts[:depth])
            entry = _entry(path)
            if entry:
                found[str(path)] = entry
        if found.get(str(home / root), ("",))[0] == "d":
            for folder, dirs, files in os.walk(home / root):
                for name in dirs + files:
                    entry = _entry(Path(folder, name))
                    if entry:
                        found[str(Path(folder, name))] = entry
    return found


def _inventory(home: Path, title: str) -> str:
    found = _snapshot(home)
    lines = [f"# {title} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"]
    lines += [f"ABSENT {home / r}" for r in ROOTS if str(home / r) not in found]
    for path, (kind, size, mtime, target) in sorted(found.items()):
        lines.append(
            f"{kind} {size} {mtime} {path}" + (f" -> {target}" if target else "")
        )
    return "\n".join(lines) + "\n"


def _tree(root: Path) -> dict[str, str]:
    found = {}
    for path in sorted(root.rglob("*")):
        key = str(path.relative_to(root))
        if path.is_symlink():
            found[key] = "link " + os.readlink(path)
        elif path.is_file():
            found[key] = _digest(path, "sha256")
        else:
            found[key] = "dir"
    return found


def _existing(target: Path, matches: Callable[[Path], bool], what: str) -> bool:
    """True for a pinned asset to reuse, False when absent; refuses the rest."""
    entry = _entry(target)
    if entry is None:
        return False
    if entry[0] == "f" and matches(target):
        return True
    kind = {"l": "a symlink", "d": "a folder", "f": f"a file that is not {what}"}
    raise InstallError(
        f"{target} is already there as {kind[entry[0]]}; refusing to overwrite it, "
        f"nothing changed. Move it away, {POINT}"
    )


def _gpg(gpg: str, folder: Path, key: Path, fingerprint: str, *verify: str) -> None:
    """Import the fetched key into a fresh keyring of its own, require it to be
    the pinned one, then require a good signature by it."""
    folder.mkdir(mode=0o700)
    base = [gpg, "--batch", "--no-autostart", "--homedir", str(folder)]

    def call(*args: str) -> tuple[int, str]:
        done = subprocess.run(
            base + list(args), capture_output=True, text=True, check=False
        )
        return done.returncode, done.stdout + done.stderr

    try:
        call("--import", str(key))
        primary, listed = False, []
        for line in call("--with-colons", "--list-keys")[1].splitlines():
            if primary and line.startswith("fpr:"):
                listed.append(line.split(":")[9])
            primary = line.startswith("pub:")
        if fingerprint not in listed:
            raise InstallError(
                f"the key fetched as {key.name} is not {fingerprint}; stopped"
            )
        code, status = call("--status-fd", "1", *verify)
    finally:  # importing makes a socket folder for this keyring outside it
        gpgconf = shutil.which("gpgconf")
        if gpgconf:
            subprocess.run([gpgconf, "--homedir", str(folder), "--remove-socketdir"],
                           capture_output=True, check=False)  # fmt: skip
    valid = [
        s.split()[-1] for s in status.splitlines() if s.startswith("[GNUPG:] VALIDSIG ")
    ]
    if code != 0 or "[GNUPG:] GOODSIG " not in status or valid != [fingerprint]:
        raise InstallError(
            f"{Path(verify[-1]).name}: no good signature by {fingerprint}; stopped"
        )


def _stage(stage: Path, gpg: str, fetch: Fetch, mise: bool, jar: bool) -> Path:
    """Fetch and check every download; nothing outside the stage changes.
    Returns the checked Java archive's extracted folder."""
    if not mise:
        fetch(MISE_URL, stage / "mise")
        _pinned(stage / "mise", "sha256", MISE_SHA256)
        for name in ("SHASUMS256.txt", "SHASUMS256.asc"):
            fetch(f"{MISE_BASE}/{name}", stage / name)
        _pinned(stage / "SHASUMS256.txt", "sha256", MISE_SUMS_SHA256)
        fetch(MISE_KEY_URL, stage / "mise-key.asc")
        signed = stage / "signed.txt"
        _gpg(gpg, stage / "gpg-mise", stage / "mise-key.asc", MISE_KEY,
             "--output", str(signed), "--decrypt", str(stage / "SHASUMS256.asc"))  # fmt: skip
        if signed.read_bytes() != (stage / "SHASUMS256.txt").read_bytes():
            raise InstallError("SHASUMS256.asc does not sign SHASUMS256.txt; stopped")
        if f"{MISE_SHA256}  ./{MISE_ASSET}" not in signed.read_text().splitlines():
            raise InstallError(f"the signed SHASUMS256.txt lacks {MISE_ASSET}; stopped")
    fetch(CATALOG_URL, stage / "catalog.json")
    entries = [
        e for e in json.loads((stage / "catalog.json").read_text())
        if e.get("vendor") == "temurin" and e.get("version") == JAVA_PIN.removeprefix("temurin-")
        and e.get("image_type") == "jdk" and "musl" not in e.get("features", [])
    ]  # fmt: skip
    if [(e.get("url"), e.get("checksum")) for e in entries] != [
        (JAVA_URL, f"sha256:{JAVA_SHA256}")
    ]:
        raise InstallError(
            f"mise's catalog does not name {JAVA_URL} with the pinned sha256; stopped"
        )
    archive = stage / JAVA_ARCHIVE
    fetch(JAVA_URL, archive)
    _pinned(archive, "sha256", JAVA_SHA256)
    fetch(JAVA_URL + ".sig", stage / "java.sig")
    fetch(JAVA_KEY_URL, stage / "java-key.asc")
    _gpg(gpg, stage / "gpg-java", stage / "java-key.asc", JAVA_KEY,
         "--verify", str(stage / "java.sig"), str(archive))  # fmt: skip
    if not jar:
        fetch(TLC_URL, stage / "tla2tools.jar")
        _pinned(stage / "tla2tools.jar", "sha256", TLC_SHA256)
        _pinned(stage / "tla2tools.jar", "sha1", TLC_SHA1)
    with tarfile.open(archive) as opened:
        if hasattr(tarfile, "tar_filter"):  # Python 3.10.12 and later
            opened.extractall(stage / "x", filter="tar")
        else:
            opened.extractall(stage / "x")
    return next((stage / "x").iterdir())


@dataclass
class _Record:
    """manifest.json: what this run created, in order, saved after each change."""

    folder: Path
    home: str
    mise: str
    status: str = "installing"
    mise_sha256: str = ""  # the checked mise this run used, reused or placed
    reused: list[str] = field(default_factory=list)
    created: list[dict[str, Any]] = field(default_factory=list)

    def add(self, *items: dict[str, Any]) -> None:
        self.created.extend(items)
        self.save()

    def save(self) -> None:
        data = {k: v for k, v in asdict(self).items() if k != "folder"}
        part = self.folder / "manifest.json.part"
        part.write_text(json.dumps(data, indent=1) + "\n")
        os.replace(part, self.folder / "manifest.json")

    def inventory(self, name: str) -> None:
        (self.folder / name).write_text(_inventory(Path(self.home), name))


def _mkdirs(folder: Path, record: _Record) -> None:
    missing = []
    while _entry(folder) is None:
        missing.append(folder)
        folder = folder.parent
    for path in reversed(missing):
        path.mkdir()
        record.add({"kind": "dir", "path": str(path)})


def _place(source: Path, target: Path, mode: int, record: _Record) -> None:
    """Create target, failing if anything is already there; never overwrites."""
    _mkdirs(target.parent, record)
    created = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode
    )
    try:
        with os.fdopen(created, "wb") as out:
            out.write(source.read_bytes())
        target.chmod(mode)
    except BaseException:
        target.unlink()
        raise
    record.add(
        {"kind": "file", "path": str(target), "sha256": _digest(source, "sha256")}
    )


def _check(java: str, jar: Path, run: Run) -> None:
    banner = run([java, "-cp", str(jar), "tlc2.TLC", "-h"])  # -h exits 1 by design
    if TLC_BANNER not in banner:
        raise InstallError(f"{java} -cp {jar} tlc2.TLC -h did not print {TLC_BANNER!r}")


def install(home: Path, fetch: Fetch = _fetch, run: Run = _run) -> list[str]:
    """Steps 1-5 of install.md; returns what it did, line by line."""
    if os.environ.get("JAVA") and os.environ.get("TLA2TOOLS"):
        java, jar = os.environ["JAVA"], Path(os.environ["TLA2TOOLS"])
        _check(java, jar, run)
        return [
            f"JAVA and TLA2TOOLS are set: nothing installed ({java}, {jar})",
            f"TLC answers: {TLC_BANNER}",
        ]
    if (platform.system(), platform.machine()) != ("Linux", "x86_64"):
        raise InstallError(
            f"the pins are for Linux x86-64; nothing changed. Use {POINT}"
        )
    gpg = shutil.which("gpg")
    if not gpg:
        raise InstallError(
            "gpg is needed to check mise's and Java's signatures and is not on PATH; "
            f"nothing changed. Install gpg, {POINT}"
        )
    mise, jar, java_dir = (
        home / ".local/bin/mise",
        jar_path(home),
        java_path(home).parents[1],
    )
    have_mise = _existing(
        mise, lambda p: _digest(p, "sha256") == MISE_SHA256, f"mise {MISE_VERSION}"
    )
    have_jar = _existing(
        jar,
        lambda p: _digest(p, "sha256") == TLC_SHA256 and _digest(p, "sha1") == TLC_SHA1,
        f"tla2tools.jar {TLC_VERSION}",
    )
    java_entry = _entry(java_dir)
    if java_entry and java_entry[0] != "d":
        _existing(java_dir, lambda p: False, "a folder")
    stage = Path(tempfile.mkdtemp(prefix="statechart-install-"))
    try:
        extracted = _stage(stage, gpg, fetch, have_mise, have_jar)
        if java_entry and _tree(java_dir) != _tree(extracted):
            raise InstallError(
                f"{java_dir} is already there and differs from the checked archive; "
                f"this run did not install it, so it is left as it is; nothing changed. {POINT}"
            )
        folder = home / RECORDS / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        folder = folder.with_name(f"{folder.name}-{os.getpid()}")
        folder.mkdir(parents=True)
        record = _Record(folder, str(home), str(mise), mise_sha256=MISE_SHA256)
        record.reused = [str(p) for p, had in
                         ((mise, have_mise), (jar, have_jar), (java_dir, java_entry)) if had]  # fmt: skip
        record.save()
        record.inventory("inventory-before.txt")
        try:
            done = _apply(home, stage, extracted, run, record)
        except BaseException as error:
            kept = _remove(record, run)
            record.status = f"failed: {error}; removed what this run created" + (
                f" except {', '.join(kept)}" if kept else ""
            )
            record.save()
            record.inventory("inventory-after.txt")
            if isinstance(error, (InstallError, OSError)):
                raise InstallError(f"{record.status}. Record: {folder}") from error
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    record.status = "installed"
    record.save()
    record.inventory("inventory-after.txt")
    return done + [
        f"TLC answers: {TLC_BANNER}",
        (
            f"record: {folder} (inventories and manifest.json; "
            f"`statechart.py install --remove {folder}` removes only what this run created)"
        ),
    ]


def _apply(
    home: Path, stage: Path, extracted: Path, run: Run, record: _Record
) -> list[str]:
    """Steps 1-3 and 5, every change recorded as it happens."""
    mise, jar, java_dir = Path(record.mise), jar_path(home), java_path(home).parents[1]
    done = []
    if str(mise) in record.reused:
        done.append(f"mise {MISE_VERSION} at {mise}: already there and pinned, reused")
    else:
        _place(stage / "mise", mise, 0o755, record)
        done.append(f"mise {MISE_VERSION} installed at {mise}")
    before = _snapshot(home)  # mise writes its own folders from here on
    try:
        if not run([str(mise), "--version"]).startswith(MISE_VERSION):
            raise InstallError(f"{mise} --version is not {MISE_VERSION}")
        if str(java_dir) in record.reused:
            done.append(
                f"Java {JAVA_PIN} at {java_dir}: already there and equal, reused"
            )
        else:
            if JAVA_PIN not in run([str(mise), "ls-remote", "java"]).split():
                raise InstallError(f"mise ls-remote java does not list {JAVA_PIN}")
            owned: dict[str, Any] = {"kind": "java", "pin": JAVA_PIN, "tree": {}}
            record.add(owned)
            try:
                run([str(mise), "install", f"java@{JAVA_PIN}"])
            finally:  # the folder was absent: all of it is this run's
                if (_entry(java_dir) or ("",))[0] == "d":
                    owned["tree"] = _tree(java_dir)
                record.save()
            where = Path(run([str(mise), "where", f"java@{JAVA_PIN}"]).strip())
            if where != java_dir or _tree(where) != _tree(extracted):
                raise InstallError(f"{where} differs from the checked archive")
            done.append(f"Java {JAVA_PIN} installed at {where}")
    finally:
        after = _snapshot(home)
        record.add(*[
            {"kind": "entry", "path": p, "entry": list(e)}
            for p, e in sorted(after.items()) if p not in before
        ])  # fmt: skip
    if str(jar) in record.reused:
        done.append(f"TLC {TLC_VERSION} at {jar}: already there and pinned, reused")
    else:
        _place(stage / "tla2tools.jar", jar, 0o644, record)
        done.append(f"TLC {TLC_VERSION} installed at {jar}")
    _check(str(java_path(home)), jar, run)
    return done


def _owned_mise(record: _Record) -> bool:
    """mise may run only while it is the checked file this run used and the
    record has not retired it (removed it once, so anything there now is new)."""
    mise = Path(record.mise)
    retired = any(
        item.get("retired") and item.get("path") == str(mise) for item in record.created
    )
    entry = _entry(mise)
    return (
        not retired and bool(record.mise_sha256) and entry is not None
        and entry[0] == "f" and _digest(mise, "sha256") == record.mise_sha256
    )  # fmt: skip


def _remove_java(record: _Record, item: dict[str, Any], run: Run) -> list[str]:
    """`mise uninstall` only a Java folder equal to the tree this run recorded,
    with the mise this run used; returns what was kept: the folder, then what
    changed or was added in it."""
    java_dir = java_path(Path(record.home)).parents[1]
    entry = _entry(java_dir)
    if entry is None:
        item["retired"] = True
        return []
    now = _tree(java_dir) if entry[0] == "d" else {}
    owned = item.get("tree") or {}
    changed = sorted(k for k in now.keys() | owned.keys() if now.get(k) != owned.get(k))
    if entry[0] == "d" and owned and not changed and _owned_mise(record):
        run([record.mise, "uninstall", f"java@{JAVA_PIN}"])
        if _entry(java_dir) is None:
            item["retired"] = True
            return []
    return [str(java_dir)] + [str(java_dir / k) for k in changed]


def _remove(record: _Record, run: Run) -> list[str]:
    """Remove what the record says this run created and still owns, newest
    first, each only while unchanged, retiring each one gone so a later run of
    the same record touches nothing that replaces it; returns what was kept."""
    kept: list[str] = []
    for item in record.created:
        if item["kind"] == "java" and not item.get("retired"):
            kept += _remove_java(record, item, run)
    for item in reversed(record.created):
        if item["kind"] == "java" or item.get("retired"):
            continue
        path = Path(item["path"])
        entry = _entry(path)
        if any(path.is_relative_to(k) for k in kept):
            continue
        if entry is None:
            item["retired"] = True
            continue
        if entry[0] == "d" and (item["kind"] == "dir" or item["entry"][0] == "d"):
            try:
                path.rmdir()
                item["retired"] = True
            except OSError:  # holds something kept or not created by this run
                if not any(Path(k).is_relative_to(path) for k in kept):
                    kept.append(str(path))
            continue
        if item["kind"] == "file":
            same = entry[0] == "f" and _digest(path, "sha256") == item["sha256"]
        else:
            same = list(entry) == item["entry"]
        if same:
            path.unlink()
            item["retired"] = True
        else:
            kept.append(str(path))
    record.save()
    return kept


def remove(folder: Path, run: Run = _run) -> list[str]:
    """Remove what the install recorded in folder created, each only while
    unchanged; returns what it did, line by line."""
    data = json.loads((folder / "manifest.json").read_text())
    record = _Record(folder, **data)
    kept = _remove(record, run)
    record.status = "removed" + (f" except {', '.join(kept)}" if kept else "")
    record.save()
    record.inventory("inventory-after-removal.txt")
    return [f"removed what {folder} records as created by its install"] + [
        f"kept (changed, or holds what the install did not create): {path}"
        for path in kept
    ]
