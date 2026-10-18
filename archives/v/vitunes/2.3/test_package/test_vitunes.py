#!/usr/bin/env python3
"""Functional test driver for the vitunes 2.3 conan package (OHOS aarch64).

vitunes ships no upstream test suite (see test_package/MANIFEST.yml for the
evidence), so this script drives the real CLI end to end:

  1. `-e help`            - the binary runs and prints the e-command list.
  2. `-e init`            - creates the database / playlist directories.
  3. `-e add <dir>`       - walks a music tree (nested directories, a tagged
                            FLAC and a non-audio file) and fills the database.
                            The tree contains a symbolic link back to an
                            ancestor: the walk must terminate and must count
                            each directory exactly once.
  4. `-e check -s <file>` - reports the meta information taglib extracted
                            through the C bindings (tag_c) of this package.
  5. `-e flush -t <fmt>`  - dumps the database (proves the entries persisted).
  6. `-e update`          - rescans the tree and reports unchanged files.

Every step asserts observable output; the script exits non-zero on the first
failed assertion.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile

EXE = None
FAILURES = []
CHECKS = 0


def check(condition, description, detail=""):
    global CHECKS
    CHECKS += 1
    if condition:
        print(f"PASS: {description}")
    else:
        print(f"FAIL: {description}")
        if detail:
            print(f"      {detail}")
        FAILURES.append(description)


def run(args, cwd=None):
    """Run the CLI and return (returncode, stdout, stderr)."""
    proc = subprocess.run([EXE] + args, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    return proc.returncode, proc.stdout


def make_tagged_flac(path, artist="Test Artist", album="Test Album",
                     title="Test Song", track="1", year="2026"):
    """Write a minimal, metadata-only FLAC file (magic + STREAMINFO +
    VORBIS_COMMENT). TagLib parses it through the C API."""
    def vorbis_comment(tags):
        vendor = b"reference libFLAC 1.3.4 20190804"
        payload = struct.pack("<I", len(vendor)) + vendor
        payload += struct.pack("<I", len(tags))
        for tag in tags:
            raw = tag.encode()
            payload += struct.pack("<I", len(raw)) + raw
        return payload

    # STREAMINFO: min/max blocksize, min/max framesize, packed
    # sample-rate/channels/bps/total-samples, md5
    streaminfo = struct.pack(">HH", 4096, 4096) + b"\x00" * 6
    packed = (44100 << 44) | (1 << 41) | (15 << 36)
    streaminfo += packed.to_bytes(8, "big") + b"\x00" * 16
    assert len(streaminfo) == 34

    blob = b"fLaC"
    blob += bytes([0x00]) + len(streaminfo).to_bytes(3, "big") + streaminfo
    comments = vorbis_comment([f"ARTIST={artist}", f"ALBUM={album}",
                               f"TITLE={title}", f"TRACKNUMBER={track}",
                               f"DATE={year}"])
    blob += bytes([0x84]) + len(comments).to_bytes(3, "big") + comments
    with open(path, "wb") as fh:
        fh.write(blob)


def main():
    global EXE
    if len(sys.argv) != 2:
        print("usage: test_vitunes.py <vitunes-binary>", file=sys.stderr)
        return 2
    EXE = os.path.abspath(sys.argv[1])
    if not os.path.isfile(EXE):
        print(f"vitunes binary not found: {EXE}", file=sys.stderr)
        return 2

    workdir = tempfile.mkdtemp(prefix="vitunes-test-")
    try:
        # ---- 1. the CLI runs and lists its e-commands --------------------
        rc, out = run(["-e", "help"])
        check(rc == 0 and "e-commands" in out and "addurl" in out,
              "vitunes -e help lists the supported e-commands",
              f"rc={rc} out={out[:200]!r}")

        db = os.path.join(workdir, "db")
        playlists = os.path.join(workdir, "playlists")

        # ---- 2. init creates the database -------------------------------
        rc, out = run(["-d", db, "-p", playlists, "-e", "init"])
        check(rc == 0 and os.path.isfile(db),
              "vitunes -e init creates the database file",
              f"rc={rc} out={out[:200]!r}")

        # ---- 3. scan a music tree (nested dirs + symlink cycle) --------
        music = os.path.join(workdir, "music")
        album = os.path.join(music, "artist1", "album1")
        sub = os.path.join(album, "sub")
        os.makedirs(sub)
        make_tagged_flac(os.path.join(album, "song1.flac"))
        make_tagged_flac(os.path.join(sub, "song2.flac"), title="Second Song")
        with open(os.path.join(music, "notes.txt"), "w") as fh:
            fh.write("not audio\n")
        # link back to the top of the tree: a walker without cycle detection
        # would descend forever
        os.symlink(music, os.path.join(sub, "loop"))

        rc, out = run(["-d", db, "-p", playlists, "-e", "add", music])
        dirs = [ln for ln in out.splitlines() if ln.startswith("Checking Directory:")]
        added = [ln for ln in out.splitlines() if ln.startswith("+ ")]
        errors = [ln for ln in out.splitlines() if ln.startswith("? ")]
        check(rc == 0, "vitunes -e add succeeds on the music tree", f"rc={rc}")
        check(len(dirs) == 4,
              "directory walk visits each directory exactly once (symlink cycle stops)",
              f"visited={len(dirs)}: {dirs}")
        check(len(added) == 2, "both tagged FLAC files are added to the database",
              f"added={added}")
        check(errors == [], "directory walk reports no errors", f"errors={errors}")
        check("(+)         2 files added" in out,
              "scan summary counts 2 added files",
              f"out={out[-400:]!r}")
        check("(s)         1 files skipped (no info)" in out,
              "non-audio file is reported as skipped",
              f"out={out[-400:]!r}")

        # ---- 4. taglib metadata extraction ------------------------------
        song = os.path.join(album, "song1.flac")
        rc, out = run(["-e", "check", "-s", song])
        check(rc == 0 and "Artist: 'Test Artist'" in out
              and "Title: 'Test Song'" in out and "Year: '2026'" in out,
              "vitunes -e check -s shows the tags read via the taglib C API",
              f"rc={rc} out={out[:400]!r}")

        # ---- 5. database content ----------------------------------------
        rc, out = run(["-d", db, "-p", playlists, "-e", "flush", "-t", "%Y"])
        check(rc == 0 and "song1.flac" in out and "song2.flac" in out
              and '"Test Artist"' in out,
              "vitunes -e flush dumps the database entries with their tags",
              f"rc={rc} out={out[:400]!r}")

        # ---- 6. rescan an unchanged tree --------------------------------
        rc, out = run(["-d", db, "-p", playlists, "-e", "update"])
        check(rc == 0 and "(.)         2 files skipped (file unchanged since last checked)" in out,
              "vitunes -e update reports the 2 unchanged files as skipped",
              f"rc={rc} out={out[-400:]!r}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    if FAILURES:
        print("failed checks:")
        for name in FAILURES:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
