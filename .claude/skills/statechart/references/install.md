# Installing Java and TLC per user

Install only with the person's approval, under their home folder: no `sudo`, no
shell-profile change, no global `mise use`. Both formal skills use this recipe.

**Pointed install.** Set `JAVA` to a Java 11+ binary and `TLA2TOOLS` to TLC
1.7.4's `tla2tools.jar`; `statechart.py install` then installs nothing and only
runs the check in step 5. Use it off Linux x86-64 or without `gpg`.

**Pinned install.** `python3 <skill-folder>/scripts/statechart.py install` (exit 2 on any stop):

1. **Before any change.** It needs Linux x86-64 and `gpg`. At each target (`~/.local/bin/mise`,
   the Java folder `~/.local/share/mise/installs/java/temurin-25.0.5+8.0.LTS`,
   `~/.local/share/tla2tools/1.7.4/tla2tools.jar`) a file matching its pin, or a Java folder
   equal to the checked archive, is reused; any other file, folder or symlink stops it.
2. **Every download, checked in a fresh temporary folder** (a reused mise or jar is not fetched). mise `2026.10.24`
   (`mise-v2026.10.24-linux-x64`, sha256 `be97dbac1c0b1fe08bd8c0cf01690f4273ea9aa02ad766b98d4e20c43eb9059d`);
   its `SHASUMS256.txt` (sha256 `587549ac3ecde92294f760bb713dc0d0a3d001b8f74c3660679686bdb47e7a40`), which
   `SHASUMS256.asc` must sign and which must list that digest. mise's Java catalog must give one glibc JDK entry
   for `temurin-25.0.5+8.0.LTS`: `OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz` from Adoptium with sha256
   `68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb`; the archive must match and its `.sig`
   must verify. TLC `1.7.4`'s jar: sha256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`,
   sha1 `bee4a54f3ee3d4afc347c3240ec2d9e93b075104` (no publisher signature exists).
   Each key comes from where its publisher says (mise: keys.openpgp.org; Adoptium: keyserver.ubuntu.com), into
   a keyring of its own, and must be the pinned fingerprint: mise `24853EC9F655CE80B48E6C3A8B81C9D17413A06D`,
   Adoptium `3B04D753C9050D9A5D343F39843C48A565F8F04B`. A failure here stops it with nothing changed.
3. **Record.** It makes `~/.local/state/statechart-install/<UTC time>-<pid>/` and writes
   `inventory-before.txt` there: every entry (type, size, modification time) under the targets and
   `~/.local/share/mise`, `~/.local/state/mise`, `~/.cache/mise` and `~/.config/mise`.
4. **Install, each change written to `manifest.json` as it happens.** mise is placed as a new file (never
   over an existing one); `mise --version` must print `2026.10.24`. If the Java folder is absent:
   `mise ls-remote java` must list it, `mise install java@temurin-25.0.5+8.0.LTS`, and every file under
   `mise where` must equal the checked archive's. The Java tree and whatever mise added are recorded. Then the jar.
5. **Check.** `java -cp <jar> tlc2.TLC -h` must print `Version 2.19 of 08 August 2024`. Then
   `inventory-after.txt`; the last output line names the record folder.

If step 4 or 5 fails, it removes what the run created (below), sets the manifest's status to the failure,
writes `inventory-after.txt` and stops.

**Removal.** `statechart.py install --remove <record folder>` removes only what that manifest says the run
created, newest first. `mise uninstall java@temurin-25.0.5+8.0.LTS` runs only if that run installed Java, the
folder equals the recorded tree and mise is the checked file the run used; else the folder stays, named with
each path changed or added in it. Then each file only while unchanged (mise and the jar by sha256, mise's files
by type, size and time, links by target), each folder only when empty; reused assets and anything changed or
added stay, named. It writes `inventory-after-removal.txt` and marks what it removed retired in the manifest, so
removing again touches and runs nothing that took its place. The record folder stays.
