#!/usr/bin/env python3
"""OHOS/HarmonyOS-specific assertions for the liggghts package.

These assert properties of the *package and its binary* that only matter on this
platform, as opposed to the physical assertions of ``test_liggghts.sh`` (which
cover the DEM solver's correctness).  Everything is parsed in pure Python - no
``readelf``/``file`` needed - so the checks also work on a bare CI worker.

usage: check_ohos.py <package_folder> [engine_path]

Checks
  A1  bin/lmp_mpi is present and a regular file
  A2  it is a real ELF binary, not a ``#!/bin/bash`` script (OHOS has no bash)
  A3  ELF64, little-endian
  A4  e_machine == AArch64 (0xB7)
  A5  e_type == ET_DYN -> position independent executable
  A6  PT_INTERP is the OHOS musl loader (/lib/ld-musl-aarch64.so.1)
  A7  every DT_NEEDED is a bare SONAME (no absolute path) and zlib is NOT among
      them (R26: a system-same-name library is linked statically)
  A8  the dynamic flags request BIND_NOW
  A9  licenses/LICENSE ships with the package
  A10 bin/lmp_mpi and licenses/LICENSE are group/other readable (HMDFS umask)
  A11 the packaged binary actually starts under the OHOS loader: `-h` prints the
      LIGGGHTS banner and the command-line help (the plain `--help`/`--version`
      spelling is NOT supported by LIGGGHTS, which is why this check uses `-h`)
"""

import os
import struct
import subprocess
import sys

ELF_MAGIC = b"\x7fELF"
EM_AARCH64 = 0xB7
ET_DYN = 3
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_FLAGS = 30
DT_FLAGS_1 = 0x6FFFFFFB
DF_1_NOW = 0x1
DF_BIND_NOW = 0x8

OHOS_INTERP = b"/lib/ld-musl-aarch64.so.1"
ALLOWED_NEEDED = {"libmpi.so.12", "libpmi.so.0", "libc++_shared.so", "libc.so"}

_failures = []
_skipped = []


def check(name, ok, detail=""):
    print("[{}] {}{}".format("ok" if ok else "FAIL", name,
                             "  -- " + detail if detail else ""))
    if not ok:
        _failures.append(name)
    return ok


def skip(name, reason=""):
    print("[skip] {}{}".format(name, "  -- " + reason if reason else ""))
    _skipped.append(name)


class Elf(object):
    """Minimal ELF64 parser: program headers + dynamic section."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.blob = fh.read()
        if self.blob[:4] != ELF_MAGIC:
            raise ValueError("not an ELF file")
        (self.e_type, self.e_machine) = struct.unpack_from("<HH", self.blob, 16)
        self.ei_class, self.ei_data = self.blob[4], self.blob[5]
        e_phoff, = struct.unpack_from("<Q", self.blob, 32)
        e_phentsize, e_phnum = struct.unpack_from("<HH", self.blob, 54)
        self.phdrs = []
        for idx in range(e_phnum):
            base = e_phoff + idx * e_phentsize
            p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, \
                p_align = struct.unpack_from("<IIQQQQQQ", self.blob, base)
            self.phdrs.append({"type": p_type, "offset": p_offset,
                               "vaddr": p_vaddr, "filesz": p_filesz})

    def _cstr(self, off, end=None):
        stop = self.blob.find(b"\0", off, end)
        return self.blob[off:stop if stop != -1 else (end or len(self.blob))]

    def interp(self):
        for ph in self.phdrs:
            if ph["type"] == PT_INTERP:
                return self._cstr(ph["offset"], ph["offset"] + ph["filesz"])
        return None

    def _vaddr_to_offset(self, addr):
        for ph in self.phdrs:
            if ph["type"] == PT_LOAD and ph["vaddr"] <= addr < ph["vaddr"] + ph["filesz"]:
                return ph["offset"] + (addr - ph["vaddr"])
        return None

    def dynamic(self):
        """Return (needed_names, flags, flags_1)."""
        dyn = next((ph for ph in self.phdrs if ph["type"] == PT_DYNAMIC), None)
        if dyn is None:
            return [], 0, 0
        entries, pos = [], dyn["offset"]
        while True:
            tag, val = struct.unpack_from("<qQ", self.blob, pos)
            pos += 16
            if tag == DT_NULL:
                break
            entries.append((tag, val))
        strtab_vaddr = dict(entries).get(DT_STRTAB, 0)
        strtab_off = self._vaddr_to_offset(strtab_vaddr) if strtab_vaddr else None
        needed = []
        for tag, val in entries:
            if tag == DT_NEEDED and strtab_off is not None:
                needed.append(self._cstr(strtab_off + val).decode("utf-8", "replace"))
        return needed, dict(entries).get(DT_FLAGS, 0), dict(entries).get(DT_FLAGS_1, 0)


def main():
    if len(sys.argv) < 2:
        print("usage: check_ohos.py <package_folder> [engine_path]")
        return 2
    pkg = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else os.path.join(pkg, "bin", "lmp_mpi")
    lic = os.path.join(pkg, "licenses", "LICENSE")

    print("package : {}".format(pkg))
    print("engine  : {}".format(engine))
    print("--- HarmonyOS-specific assertions ---")

    # A1 -- the packaged binary exists
    if not check("A1 bin/lmp_mpi present", os.path.isfile(engine)):
        print("\nOHOS-specific assertions: aborted (no engine)")
        return 1

    # A2 -- real binary, not a shell script: OHOS images have no /bin/bash, so a
    #       wrapper script would be unusable there.
    with open(engine, "rb") as fh:
        head = fh.read(2)
    check("A2 ELF binary, not a #! script", head == ELF_MAGIC[:2],
          "first bytes: {!r}".format(head))

    try:
        elf = Elf(engine)
    except ValueError as exc:
        check("A2 ELF binary, not a #! script", False, str(exc))
        print("\nOHOS-specific assertions: aborted (not an ELF file)")
        return 1

    # A3/A4/A5 -- 64-bit little-endian AArch64 PIE
    check("A3 ELF64 little-endian",
          elf.ei_class == 2 and elf.ei_data == 1,
          "class={} data={}".format(elf.ei_class, elf.ei_data))
    check("A4 machine is AArch64", elf.e_machine == EM_AARCH64,
          "e_machine=0x{:x}".format(elf.e_machine))
    check("A5 ET_DYN (PIE)", elf.e_type == ET_DYN, "e_type={}".format(elf.e_type))

    # A6 -- the OHOS loader is what will run it on the device
    interp = elf.interp()
    check("A6 interpreter is OHOS musl loader", interp == OHOS_INTERP,
          "PT_INTERP={!r}".format(interp))

    needed, d_flags, flags_1 = elf.dynamic()

    # A7 -- no absolute-path dependencies (they would break the sandbox layout),
    #       and no dynamic libz: LIGGGHTS' gzip support shells out to `gunzip`
    #       (src/read_data.cpp) and zlib is only referenced from image.cpp under
    #       #ifdef LAMMPS_PNG, so the engine references no zlib symbol at all.
    #       R26 (a system-same-name library must not be linked dynamically) is
    #       therefore satisfied with nothing to link.
    absolute = [n for n in needed if "/" in n]
    check("A7a no absolute DT_NEEDED", not absolute, "absolute: {}".format(absolute))
    check("A7b zlib not a dynamic dependency", not any("libz.so" in n for n in needed),
          "needed: {}".format(needed))
    unexpected = sorted(set(needed) - ALLOWED_NEEDED)
    check("A7c only expected shared libraries", not unexpected,
          "unexpected: {} / all: {}".format(unexpected, needed))

    # A8 -- BIND_NOW (matches the L4 security expectation for this target)
    bind_now = bool(flags_1 & DF_1_NOW) or bool(d_flags & DF_BIND_NOW)
    check("A8 BIND_NOW set", bind_now,
          "DT_FLAGS=0x{:x} DT_FLAGS_1=0x{:x}".format(d_flags, flags_1))

    # A9 -- license ships with the package
    check("A9 licenses/LICENSE present", os.path.isfile(lic))

    # A10 -- HMDFS may drop permissions; the package must stay readable by
    #        group/other or consumers cannot read it
    for label, path in (("bin/lmp_mpi", engine), ("licenses/LICENSE", lic)):
        if os.path.isfile(path):
            mode = os.stat(path).st_mode & 0o777
            check("A10 {} group/other readable".format(label), bool(mode & 0o044),
                  "mode=0o{:o}".format(mode))

    # A11 -- the packaged binary really starts under the OHOS loader.  LIGGGHTS
    #        has no --version/--help; `-h` is its documented help switch, and it
    #        exits with status 1 by upstream convention (src/error.cpp
    #        Error::done() ends in exit(1); the help flag takes that path).
    try:
        proc = subprocess.run([engine, "-h"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=120)
        out = proc.stdout.decode("utf-8", "replace")
        check("A11a -h exits 1 (upstream convention)", proc.returncode == 1,
              "rc={}".format(proc.returncode))
        check("A11b banner printed", "LIGGGHTS-PUBLIC" in out,
              out.splitlines()[0] if out.splitlines() else "no output")
        check("A11c help text printed", "-in filename" in out and "-log" in out)
    except Exception as exc:
        check("A11 package binary runs under OHOS loader", False, str(exc))

    print("\nOHOS-specific assertions: {} failed, {} skipped".format(
        len(_failures), len(_skipped)))
    if _failures:
        print("failed: {}".format(", ".join(_failures)))
        return 1
    print("All OHOS-specific assertions passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
