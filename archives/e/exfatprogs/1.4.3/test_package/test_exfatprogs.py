#!/usr/bin/env python3
"""Consumer assertions for exfatprogs 1.4.3 on HarmonyOS PC.

Every assertion runs against a regular file image (the S_ISREG path), which is
the upstream-supported, unprivileged surface on this platform:

  1. all six packaged binaries are present in bindir
  2. mkfs.exfat -L TESTVOL formats a 64 MiB regular file (rc == 0)
  3. dump.exfat reports the volume label written by mkfs
  4. dump.exfat reports a plausible cluster size
  5. fsck.exfat -y accepts the freshly formatted image (rc == 0, "clean")
  6. exfatlabel rewrites the label and dump.exfat reads it back verbatim
  7. negative control: fsck.exfat -y on a zero-filled file must fail

The block-device/mount face (losetup, /dev/loop*, mount) is unavailable to
unprivileged users on this platform; it is a different face of the tool, not
this deliverable's asserted surface, so it is intentionally not tested here.
"""

import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = (
    "mkfs.exfat",
    "fsck.exfat",
    "tune.exfat",
    "exfatlabel",
    "dump.exfat",
    "exfat2img",
)

CHECKS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"{status}: {name}" + (f" ({detail})" if detail else ""))
    CHECKS.append((name, bool(cond)))


def run(args, timeout=300):
    proc = subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=False
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _workdir():
    """Scratch dir OUTSIDE the recipe tree (device /tmp is read-only; writing
    next to test_package would drop multi-hundred-MB images into the repo)."""
    bases = [b for b in (os.environ.get("TMPDIR"),
                         os.path.join(os.path.expanduser("~"), "tmp")) if b]
    bases.append(os.getcwd())
    for base in bases:
        try:
            os.makedirs(base, exist_ok=True)
            if os.access(base, os.W_OK):
                return tempfile.mkdtemp(prefix="exfatprogs-consumer-", dir=base)
        except OSError:
            continue
    raise SystemExit("no writable scratch directory for the consumer test")


def main(bindir):
    tools = {name: os.path.join(bindir, name) for name in TOOLS}
    check(
        "six packaged binaries present in bindir",
        all(os.path.isfile(p) for p in tools.values()),
        ",".join(sorted(os.path.basename(p) for p in tools.values()
                        if os.path.isfile(p))),
    )

    workdir = _workdir()
    try:
        img = os.path.join(workdir, "consumer.img")
        with open(img, "wb") as handle:
            handle.truncate(64 * 1024 * 1024)

        rc, out = run([tools["mkfs.exfat"], "-L", "TESTVOL", img])
        check("mkfs.exfat formats a regular file image", rc == 0, f"rc={rc}")

        rc, out = run([tools["dump.exfat"], img])
        check("mkfs wrote the requested volume label",
              rc == 0 and "Volume label:" in out and "TESTVOL" in out,
              f"rc={rc}")
        check("dump.exfat reports a cluster size",
              rc == 0 and "Cluster size:" in out,
              [ln for ln in out.splitlines() if "Cluster size" in ln][:1])

        rc, out = run([tools["fsck.exfat"], "-y", img])
        check("fsck.exfat -y accepts the freshly formatted image",
              rc == 0 and "clean" in out, f"rc={rc}")

        rc, out = run([tools["exfatlabel"], img, "RENAMED"])
        check("exfatlabel rewrites the volume label", rc == 0, f"rc={rc}")
        rc, out = run([tools["dump.exfat"], img])
        check("dump.exfat reads back the new label RENAMED",
              rc == 0 and "RENAMED" in out, f"rc={rc}")

        blank = os.path.join(workdir, "not-exfat.img")
        with open(blank, "wb") as handle:
            handle.truncate(1024 * 1024)
        rc, out = run([tools["fsck.exfat"], "-y", blank])
        check("negative control: fsck.exfat rejects a zero-filled file",
              rc != 0, f"rc={rc}")

        passed = sum(1 for _, ok in CHECKS if ok)
        total = len(CHECKS)
        print(f"CONSUMER ASSERTIONS: {passed}/{total} passed")
        if passed != total:
            print("FAILED:", [name for name, ok in CHECKS if not ok])
            return 1
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_exfatprogs.py <bindir>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
