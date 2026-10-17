#!/usr/bin/env python3
"""Restore a valid OpenHarmony ``.codesign`` block in ELF files.

OHOS refuses to execute an ELF whose ``.codesign`` record does not match the
file (``execve`` fails with EPERM / "Operation not permitted").  The record is
written by the OHOS-patched ``ld.lld --code-sign`` pass, which produces an
*inconsistent* record when linking against a large static archive: every
executable that links ``libdynamorio_static.a`` ends up with a recorded length
that does not match the file size, and is therefore not executable on OHOS.

This helper re-generates the signature with the platform tools:

1. ``llvm-objcopy --remove-section=.codesign``  (the signer refuses files that
   already carry a ``.codesign`` section),
2. ``binary-sign-tool sign -selfSign 1``,
3. install the result atomically (an already-signed file refuses in-place
   overwrite, so the new file is renamed over the old one, with a
   remove-then-copy fallback).

All steps are skipped gracefully when the OHOS signing tools are unavailable
(non-OHOS build hosts); callers can tell the difference because ``resign_tree``
reports files it could not repair.

Usage::

    python3 ohos_resign.py <file-or-directory> [...]
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile

_OBJCOPY_CANDIDATES = ("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
_SIGN_CANDIDATES = ("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
# readelf is not guaranteed to be on PATH inside the CI conan build environment
# (the OHOS SDK installs it under /data/service/hnp/bin, which that environment
# does not inherit), so resolve it explicitly like the signing tools.
_READELF_CANDIDATES = ("readelf", "/data/service/hnp/bin/readelf",
                       "/data/service/hnp/bin/llvm-readelf")

OK = "ok"
NO_CODESIGN = "no-codesign"
UNREADABLE = "unreadable"


def _find(candidates):
    for cand in candidates:
        if os.path.isabs(cand):
            if os.path.exists(cand):
                return cand
        else:
            found = shutil.which(cand)
            if found:
                return found
    return None


def read_codesign(path):
    """Inspect the .codesign record of *path*.

    Returns (OK, section_offset, recorded_length, file_size),
    (NO_CODESIGN,) when the file carries no .codesign section, or
    (UNREADABLE, reason) when the record could not be inspected (so that a
    caller never mistakes a failed probe for "nothing to do").
    """
    readelf = _find(_READELF_CANDIDATES)
    if readelf is None:
        return (UNREADABLE, "no readelf/llvm-readelf available to inspect .codesign")
    try:
        proc = subprocess.run([readelf, "-SW", path], capture_output=True, text=True,
                              timeout=60)
    except Exception as exc:  # readelf missing / timed out
        return (UNREADABLE, "readelf failed to run: %s" % exc)
    if proc.returncode != 0:
        return (UNREADABLE, "readelf exited %d" % proc.returncode)
    off = None
    for line in proc.stdout.splitlines():
        if ".codesign" in line:
            parts = line.split()
            try:
                off = int(parts[parts.index(".codesign") + 3], 16)
            except (ValueError, IndexError):
                return (UNREADABLE, "could not parse the .codesign section header")
    if off is None:
        return (NO_CODESIGN,)
    size = os.path.getsize(path)
    if off + 0x18 > size:
        return (UNREADABLE, ".codesign header runs past end of file")
    with open(path, "rb") as fh:
        fh.seek(off + 0x10)
        recorded = struct.unpack("<Q", fh.read(8))[0]
    return (OK, off, recorded, size)


def is_elf(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x7fELF"
    except Exception:
        return False


def needs_resign(path):
    info = read_codesign(path)
    if info[0] != OK:
        return False  # nothing to repair (or undecidable: reported separately)
    _, _off, recorded, size = info
    return recorded != size


def install_atomically(src, dst):
    """Replace *dst* with *src*, preferring an atomic rename.

    Signed files refuse in-place overwrite on OHOS, so a remove-then-copy
    fallback is kept for filesystems where rename-over-existing is refused.
    """
    try:
        os.replace(src, dst)
    except OSError:
        try:
            os.remove(dst)
        except OSError:
            pass
        shutil.copy2(src, dst)
    os.chmod(dst, 0o755)


def resign(path, objcopy=None, signer=None, verbose=True):
    """Return True when the file needed and received a fresh signature."""
    objcopy = objcopy or _find(_OBJCOPY_CANDIDATES)
    signer = signer or _find(_SIGN_CANDIDATES)
    if not objcopy or not signer:
        if verbose:
            print("[ohos_resign] OHOS signing tools unavailable; skipping " + path)
        return False
    if not needs_resign(path):
        return False
    tmp = tempfile.mkdtemp(prefix="ohos-resign-")
    try:
        unsigned = os.path.join(tmp, "unsigned.elf")
        signed = os.path.join(tmp, "signed.elf")
        if subprocess.run([objcopy, "--remove-section=.codesign", path, unsigned],
                          capture_output=True).returncode != 0:
            return False
        if subprocess.run([signer, "sign", "-selfSign", "1", "-inFile", unsigned,
                           "-outFile", signed], capture_output=True, timeout=600).returncode != 0:
            return False
        if not os.path.exists(signed):
            return False
        install_atomically(signed, path)
        if verbose:
            print("[ohos_resign] re-signed {}".format(path))
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def resign_tree(root, verbose=True):
    """Repair every repairable ELF below *root*.

    Returns (repaired_count, problems) where *problems* lists
    (path, reason) for files that still carry an inconsistent record after the
    attempt, or that could not be inspected at all -- the caller can then fail
    loudly instead of reporting a false success.
    """
    repaired = 0
    problems = []
    tools_available = _find(_OBJCOPY_CANDIDATES) is not None and _find(_SIGN_CANDIDATES) is not None
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not is_elf(path):
                continue
            info = read_codesign(path)
            if info[0] == UNREADABLE:
                problems.append((path, info[1]))
                continue
            if info[0] == NO_CODESIGN:
                continue
            if resign(path, verbose=verbose):
                repaired += 1
            elif tools_available:
                after = read_codesign(path)
                if after[0] != OK or after[2] != after[3]:
                    problems.append((path, "signature still inconsistent after repair"))
    if verbose:
        print("[ohos_resign] {} file(s) re-signed under {} ({} problem(s))".format(
            repaired, root, len(problems)))
    return repaired, problems


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    total = 0
    problems = []
    for target in argv[1:]:
        if os.path.isdir(target):
            n, p = resign_tree(target)
            total += n
            problems += p
        elif resign(target):
            total += 1
    print("[ohos_resign] total re-signed: {}".format(total))
    for path, reason in problems:
        print("[ohos_resign] PROBLEM {}: {}".format(path, reason))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
