#!/usr/bin/env python3
"""End-to-end execution tests for the packaged gptfdisk binaries (R34).

Runs the real CLI tools on a scratch 64 MiB image file (no block device
needed, same approach as the upstream gdisk_test.sh):

  * sgdisk: --version, zap (-Z), new partition (-n), type (-t), name (-c),
    print (-p), info (-i), backup (-b), wipe (-Z), restore (-l), print again;
  * on-disk signatures: GPT header magic "EFI PART" at LBA1 and the
    protective-MBR 0x55AA signature;
  * gdisk: a piped p/q session against the image (prints the partition);
  * fixparts: MBR repair tool, run with EOF stdin (prints banner + loads
    the MBR; it is interactive, so only the load path is asserted);
  * cgdisk: full-screen curses tool; without a TTY it must terminate
    through the documented ncurses terminal-init error path (proves the
    binary loads and reaches curses initialisation; no silent crash).

Every check is a real subprocess exit code / output assertion. Fail closed:
any FAIL exits 1. Prints E2E_ASSERTIONS=<n> PASSED=<p> FAILED=<f>.
Usage: python3 test_gptfdisk_e2e.py <bin-dir>
"""
import os
import shutil
import subprocess
import sys
import tempfile

VERSION = "1.0.10"
TOOLS = ("gdisk", "cgdisk", "sgdisk", "fixparts")


class Reporter:
    def __init__(self):
        self.passed = 0
        self.failed = []

    def check(self, cond, label):
        if cond:
            self.passed += 1
            print("PASS {}".format(label))
        else:
            self.failed.append(label)
            print("FAIL {}".format(label))


def run(args, **kwargs):
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.STDOUT)
    kwargs.setdefault("timeout", 180)
    return subprocess.run(args, universal_newlines=True, **kwargs)


def main():
    if len(sys.argv) < 2:
        print("usage: test_gptfdisk_e2e.py <bin-dir>")
        return 2
    bindir = sys.argv[1]
    r = Reporter()
    bins = {t: os.path.join(bindir, t) for t in TOOLS}

    # 1) all four CLI tools packaged and non-empty
    for tool, path in bins.items():
        r.check(os.path.isfile(path) and os.path.getsize(path) > 0,
                "{}: packaged non-empty binary".format(tool))

    # scratch image (TMPDIR is writable on the build machine; R10)
    scratch = os.environ.get("TMPDIR") or None
    if not scratch or not os.path.isdir(scratch):
        scratch = None
    tmpdir = tempfile.mkdtemp(prefix="gptfdisk-e2e-", dir=scratch)
    img = os.path.join(tmpdir, "disk.img")
    backup = os.path.join(tmpdir, "gpt-backup.bin")
    with open(img, "wb") as fh:
        fh.truncate(64 * 1024 * 1024)

    try:
        sgdisk = bins["sgdisk"]

        # 2) version banner
        p = run([sgdisk, "--version"])
        r.check(p.returncode == 0 and VERSION in (p.stdout or ""),
                "sgdisk --version prints {}".format(VERSION))

        # 3) zap (create empty GPT)
        p = run([sgdisk, "-Z", img])
        r.check(p.returncode == 0, "sgdisk -Z (new empty GPT) rc=0")

        # 4-6) create a 16 MiB Linux partition
        p = run([sgdisk, "-n", "1:2048:+16M", img])
        r.check(p.returncode == 0, "sgdisk -n 1:2048:+16M rc=0")
        p = run([sgdisk, "-t", "1:8300", img])
        r.check(p.returncode == 0, "sgdisk -t 1:8300 (Linux filesystem) rc=0")
        p = run([sgdisk, "-c", "1:OHOSTEST", img])
        r.check(p.returncode == 0, "sgdisk -c 1:OHOSTEST rc=0")

        # 7) print table: rc, partition name, partition type code
        p = run([sgdisk, "-p", img])
        out = p.stdout or ""
        r.check(p.returncode == 0, "sgdisk -p rc=0")
        r.check("OHOSTEST" in out, "sgdisk -p shows partition name OHOSTEST")
        r.check("8300" in out, "sgdisk -p shows Linux type code 8300")

        # 8) partition info
        p = run([sgdisk, "-i", "1", img])
        out = p.stdout or ""
        r.check(p.returncode == 0, "sgdisk -i 1 rc=0")
        r.check("OHOSTEST" in out, "sgdisk -i 1 shows partition name")

        # 9) backup GPT data to a file
        p = run([sgdisk, "-b", backup, img])
        r.check(p.returncode == 0, "sgdisk -b backup rc=0")
        r.check(os.path.isfile(backup) and os.path.getsize(backup) > 0,
                "GPT backup file non-empty")

        # 10) wipe, then restore from the backup
        p = run([sgdisk, "-Z", img])
        r.check(p.returncode == 0, "sgdisk -Z (wipe before restore) rc=0")
        p = run([sgdisk, "-l", backup, img])
        r.check(p.returncode == 0, "sgdisk -l (restore backup) rc=0")
        p = run([sgdisk, "-p", img])
        r.check("OHOSTEST" in (p.stdout or ""),
                "restored GPT still lists partition OHOSTEST")

        # 11) on-disk signatures: GPT header magic + protective MBR
        with open(img, "rb") as fh:
            fh.seek(510)
            mbr_sig = fh.read(6)  # 2 bytes MBR sig + pad
            fh.seek(512)
            gpt_magic = fh.read(8)
        r.check(gpt_magic == b"EFI PART", "GPT header magic 'EFI PART' at LBA1")
        r.check(mbr_sig[:2] == b"\x55\xaa", "protective MBR signature 0x55AA")

        # 12) gdisk interactive, driven through a piped p/q session
        p = run([bins["gdisk"], img], input="p\nq\n")
        out = p.stdout or ""
        r.check(p.returncode == 0, "gdisk piped p/q session rc=0")
        r.check(VERSION in out, "gdisk prints version {}".format(VERSION))
        r.check("OHOSTEST" in out, "gdisk table listing shows partition")

        # 13) fixparts (MBR repair tool): banner + MBR load path.
        #     It is interactive; EOF on stdin is the documented exit path.
        p = run([bins["fixparts"], img], input="q\n")
        out = p.stdout or ""
        r.check("FixParts {}".format(VERSION) in out,
                "fixparts prints FixParts {}".format(VERSION))
        r.check("Loading MBR data from" in out, "fixparts loads the MBR")

        # 14) cgdisk (curses UI): without a TTY it must fail through the
        #     documented ncurses terminal-init path, not crash silently.
        env = os.environ.copy()
        env["TERM"] = "dumb"
        p = run([bins["cgdisk"], img], env=env, stdin=subprocess.DEVNULL)
        out = p.stdout or ""
        r.check(p.returncode != 0,
                "cgdisk without TTY exits non-zero (rc={})".format(p.returncode))
        r.check(("cannot initialize terminal" in out)
                or ("Error opening terminal" in out),
                "cgdisk reached ncurses terminal-init error path")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = r.passed + len(r.failed)
    print("E2E_ASSERTIONS={} PASSED={} FAILED={}".format(
        total, r.passed, len(r.failed)))
    if r.failed:
        print("FAILED CHECKS:")
        for f in r.failed:
            print("  -", f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
