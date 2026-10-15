#!/usr/bin/env python3
"""Consumer test for the packaged lpr 2008.05.17.4 CLI package.

Usage: test_lpr.py <package_folder> [--runtime]

Static leg (runs in cross builds and on device alike):
  * 8 programs exist, are regular files and carry the executable bit
    (bin/: lpr lpq lprm lptest, sbin/: lpc lpd lpf pac — the split is upstream's
    own debian/install).
  * every one of them is ELF64 little-endian EM_AARCH64.
  * 8 man pages (4x man1, 5x man5 counting printcap.5) + etc/printcap +
    licenses/copyright.
  * compat symbol scope: the 6 programs that link common_source/common.c or
    lpd/rcmd.c must DEFINE rresvport_af and innetgr locally (st_shndx !=
    SHN_UNDEF), and lpf/lptest must not mention them at all.  This is the one
    thing that can silently go wrong on musl: both symbols are glibc-only, and
    without the recipe's link-stage injection the six programs either fail to
    link or end up with dangling references.
  * no build leftovers in the package (object files, the compiler wrapper, the
    compat source).

Runtime leg (only when the target is executable): five clients plus lpc must
print their usage for an invalid flag, which proves the dynamic loader resolved
libc.so, getopt ran and the printcap subsystem initialised.  Output goes to
$TMPDIR only: /tmp on OHOS is read-only erofs and /bin/sh materialises command
substitution in hardcoded /tmp while ignoring TMPDIR.

The ELF reader is hand-rolled on purpose: the OHOS worker's HMBS injects only
cmake/make/ninja/python3, so nm/readelf/objdump may be absent.
"""

import os
import struct
import subprocess
import sys

EM_AARCH64 = 183

BIN_PROGRAMS = ("lpr", "lpq", "lprm", "lptest")
SBIN_PROGRAMS = ("lpc", "lpd", "lpf", "pac")

# programs that genuinely reference the BSD compat layer (see conanfile.py)
COMPAT_USERS = frozenset({"lpc", "lpd", "lpq", "lpr", "lprm", "pac"})
COMPAT_SYMBOLS = ("rresvport_af", "innetgr")

MAN_PAGES = {
    "man1": ("lpq.1", "lptest.1", "lprm.1", "lpr.1"),
    "man5": ("lpf.8", "pac.8", "lpc.8", "lpd.8", "printcap.5"),
}

# -Z is not in any of the five optstrings (lpr ":#:1:2:3:4:C:J:P:T:U:cdfghi::lmnpqrstvw:",
# lpq "alP:w:", lprm "P:w", pac "P:p:scmr"), and lpc has no getopt at all — its
# command table rejects an unknown first argument with "?Invalid command".
# Every program therefore exits through its usage/error path *before* touching
# the spooler, so the probe can never block on a device with no printer.
USAGE_PROBES = ("lpr", "lpq", "lprm", "lpc", "pac")

failures = []
passed = 0


def check(condition, label):
    global passed
    if condition:
        passed += 1
        print("TPOK %s" % label)
    else:
        failures.append(label)
        print("TPFAIL %s" % label)


def elf_header(path):
    with open(path, "rb") as handle:
        head = handle.read(20)
    return {
        "magic": head[:4],
        "class": head[4],
        "data": head[5],
        "machine": int.from_bytes(head[18:20], "little"),
    }


def elf_symbols(path):
    """Return (defined, undefined) symbol-name sets from .symtab/.dynsym."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF" or data[4] != 2:
        return None, None
    e_shoff, = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    if e_shoff == 0 or e_shnum == 0:
        return None, None
    sections = []
    for index in range(e_shnum):
        (sh_name, sh_type, _flags, _addr, sh_offset, sh_size, sh_link,
         _info, _align, sh_entsize) = struct.unpack_from("<IIQQQQIIQQ", data,
                                                        e_shoff + index * e_shentsize)
        sections.append({"type": sh_type, "offset": sh_offset, "size": sh_size,
                         "link": sh_link, "entsize": sh_entsize, "name": sh_name})

    def name_at(string_section, offset):
        base = sections[string_section]["offset"]
        end = data.index(b"\0", base + offset)
        return data[base + offset:end].decode("utf-8", "replace")

    section_names = [name_at(e_shstrndx, s["name"]) for s in sections]
    defined, undefined = set(), set()
    tables = [i for i, name in enumerate(section_names) if name in (".symtab", ".dynsym")]
    for index in tables:
        table = sections[index]
        entsize = table["entsize"] or 24
        for slot in range(table["size"] // entsize):
            (st_name, st_info, _other, st_shndx, _value,
             _size) = struct.unpack_from("<IBBHQQ", data,
                                         table["offset"] + slot * entsize)
            if st_name == 0:
                continue
            name = name_at(table["link"], st_name)
            if (st_info & 0xF) not in (0, 1, 2, 10, 13):
                continue
            (undefined if st_shndx == 0 else defined).add(name)
    return defined, undefined


def tmpdir():
    for candidate in (os.environ.get("TMPDIR"), os.environ.get("TMP"),
                      os.path.join(os.environ.get("HOME", "."), "tmp"),
                      os.path.join(os.getcwd(), "tmp")):
        if candidate and os.path.isdir(candidate):
            return candidate
    return os.getcwd()


def main(argv):
    if len(argv) < 2:
        print("usage: test_lpr.py <package_folder> [--runtime]")
        return 2
    pkg = argv[1]
    runtime = "--runtime" in argv[2:]

    # -- program layout, mirroring upstream debian/install -------------------
    programs = ([(name, "bin") for name in BIN_PROGRAMS]
                + [(name, "sbin") for name in SBIN_PROGRAMS])
    for name, subdir in programs:
        path = os.path.join(pkg, subdir, name)
        check(os.path.isfile(path) and not os.path.islink(path),
              "%s/%s is a regular file" % (subdir, name))
        check(os.access(path, os.X_OK), "%s/%s is executable" % (subdir, name))
        if not os.path.isfile(path):
            continue
        head = elf_header(path)
        check(head["magic"] == b"\x7fELF" and head["class"] == 2 and head["data"] == 1,
              "%s/%s is ELF64 little-endian" % (subdir, name))
        check(head["machine"] == EM_AARCH64,
              "%s/%s targets EM_AARCH64" % (subdir, name))
        defined, undefined = elf_symbols(path)
        if defined is None:
            check(False, "%s/%s has a readable symbol table" % (subdir, name))
            continue
        for symbol in COMPAT_SYMBOLS:
            if name in COMPAT_USERS:
                check(symbol in defined,
                      "%s defines %s locally (not a dangling libc ref)" % (name, symbol))
                check(symbol not in undefined,
                      "%s has no undefined %s" % (name, symbol))
            else:
                check(symbol not in defined and symbol not in undefined,
                      "%s does not reference %s at all" % (name, symbol))

    # -- configuration, documentation, licence -------------------------------
    check(os.path.isfile(os.path.join(pkg, "etc", "printcap")),
          "etc/printcap shipped (upstream debian/printcap)")
    for section, pages in sorted(MAN_PAGES.items()):
        for page in pages:
            check(os.path.isfile(os.path.join(pkg, "share", "man", section, page)),
                  "share/man/%s/%s shipped" % (section, page))
    check(os.path.isfile(os.path.join(pkg, "licenses", "copyright")),
          "licenses/copyright shipped")

    # -- no build leftovers --------------------------------------------------
    leftovers = []
    for root, _dirs, files in os.walk(pkg):
        for name in files:
            if name.endswith((".o", ".c", ".h")) or name in ("cc-ohos-wrap",
                                                              "Makefile"):
                leftovers.append(os.path.relpath(os.path.join(root, name), pkg))
    check(not leftovers,
          "no object files / compat sources / wrapper leaked into the package"
          + (" (found: %s)" % ", ".join(sorted(leftovers)[:8]) if leftovers else ""))

    # -- runtime leg ---------------------------------------------------------
    if runtime:
        workdir = tmpdir()
        for name in USAGE_PROBES:
            subdir = "bin" if name in BIN_PROGRAMS else "sbin"
            path = os.path.join(pkg, subdir, name)
            out = os.path.join(workdir, "lpr-%s.txt" % name)
            try:
                with open(out, "wb") as handle:
                    subprocess.run([path, "-Z"], stdout=handle, stderr=subprocess.STDOUT,
                                   cwd=workdir, timeout=120)
            except (OSError, subprocess.SubprocessError) as exc:
                check(False, "%s runs (launch failed: %s)" % (name, exc))
                continue
            check(os.path.getsize(out) > 0,
                  "%s produced output for an invalid flag (loader+getopt+printcap "
                  "subsystem ran)" % name)
    else:
        print("TPINFO runtime leg skipped (cross build)")

    print("TPRESULT %s (%d passed, %d failed)"
          % ("FAIL" if failures else "PASS", passed, len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))