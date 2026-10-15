#!/usr/bin/env python3
"""HarmonyOS artifact/ABI checks for the packaged smalt 0.7.6 binaries.

Pure Python ELF parsing, no external tool: these checks inspect the
cross-compiled artifacts instead of executing them, so they run on *any* build
host - including the macOS dev box that cross-compiles with the OHOS SDK but
cannot execute an aarch64-linux-ohos ELF (can_run() is False there).  They are
also what makes the CI L1e destructive reverse check meaningful when cross
building: move bin/ away and this layer fails.

Checks (each is one independently judged item; every binary in bin/ must
satisfy it, so one item covers all ten executables):

  A1  ELF64, little endian, e_machine == EM_AARCH64 and e_type == ET_DYN
      HarmonyOS PC is aarch64 and its toolchain produces PIE executables; an
      x86_64 or non-PIE build fails here.
  A2  PT_INTERP == /lib/ld-musl-aarch64.so.1
      OHOS ships musl.  A glibc-targeted toolchain emits
      /lib/ld-linux-aarch64.so.1, so this separates "really built for OHOS"
      from "built for some other aarch64 Linux".
  A3  DT_NEEDED carries no libz / libm / libpthread / libc++ and does carry
      libc.so
      zlib is consumed from its static OHOS package (R26: a system-name
      library must not be dropped into the OHOS /lib), and musl provides libm
      and libpthread as empty compatibility archives, so upstream's
      `-lm -lpthread -lz` link line must leave exactly one runtime dependency
      behind.  Measured on the cross-built package: NEEDED = [libc.so].
  A4  no DT_RPATH and no DT_RUNPATH
      OHOS packages are staged into a versioned prefix and moved out of the
      conan cache; a build-time RPATH would make the loader look for libraries
      that only exist on the build machine.

Exit code 0 = every check passed, 1 = at least one failure.
"""
import argparse
import os
import struct
import sys

ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_DYN = 3
EM_AARCH64 = 183
PT_INTERP = 3
PT_GNU_STACK = 0x6474E551
SHT_DYNAMIC = 6
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_RPATH = 15
DT_RUNPATH = 29

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"
FORBIDDEN_PREFIXES = ("libz", "libm", "libpthread", "libc++", "libstdc++")


class ElfError(Exception):
    pass


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def parse_elf(data, path):
    """Return a dict with the facts the checks need."""
    if data[:4] != b"\x7fELF":
        raise ElfError("%s: not an ELF file (magic %r)" % (path, data[:4]))
    if data[4] != ELFCLASS64:
        raise ElfError("%s: not ELF64 (EI_CLASS=%d)" % (path, data[4]))
    if data[5] != ELFDATA2LSB:
        raise ElfError("%s: not little endian (EI_DATA=%d)" % (path, data[5]))
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    e_phoff, e_shoff = struct.unpack_from("<QQ", data, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 58)

    interp = None
    nx_stack = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags = struct.unpack_from("<II", data, off)
        p_offset, _va, _pa, p_filesz = struct.unpack_from("<QQQQ", data, off + 8)
        if p_type == PT_INTERP:
            interp = data[p_offset:p_offset + p_filesz].rstrip(b"\x00").decode(
                "utf-8", "replace")
        elif p_type == PT_GNU_STACK:
            nx_stack = not (p_flags & 0x1)

    # .dynamic, located through the section headers
    needed, rpath, runpath = [], None, None
    if e_shoff and e_shnum:
        dyn_off = dyn_size = dyn_link = None
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            _name, sh_type = struct.unpack_from("<II", data, off)
            # sh_flags(Q) sh_addr(Q) sh_offset(Q) sh_size(Q) sh_link(I) sh_info(I)
            _flags, _addr, sh_offset, sh_size, sh_link, _info = struct.unpack_from(
                "<QQQQII", data, off + 8)
            if sh_type == SHT_DYNAMIC:
                dyn_off, dyn_size, dyn_link = sh_offset, sh_size, sh_link
                break
        if dyn_off is not None:
            strtab_off = strtab_size = None
            if dyn_link < e_shnum:
                off = e_shoff + dyn_link * e_shentsize
                _n, _t, _f, _a, strtab_off, strtab_size = struct.unpack_from(
                    "<IIQQQQ", data, off)
            strtab = data[strtab_off:strtab_off + strtab_size] if strtab_off else b""
            for pos in range(dyn_off, dyn_off + dyn_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", data, pos)
                if d_tag == DT_NULL:
                    break
                if d_tag in (DT_NEEDED, DT_RPATH, DT_RUNPATH):
                    end = strtab.find(b"\x00", d_val)
                    name = strtab[d_val:end].decode("utf-8", "replace")
                    if d_tag == DT_NEEDED:
                        needed.append(name)
                    elif d_tag == DT_RPATH:
                        rpath = name
                    else:
                        runpath = name
    return {"path": path, "e_type": e_type, "e_machine": e_machine,
            "interp": interp, "needed": needed, "rpath": rpath,
            "runpath": runpath, "nx_stack": nx_stack}


def list_binaries(bindir):
    out = []
    for name in sorted(os.listdir(bindir)):
        path = os.path.join(bindir, name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            out.append(path)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bindir", required=True, help="bin/ of the tested package")
    args = ap.parse_args()

    binaries = list_binaries(args.bindir)
    if not binaries:
        print("FAIL A0 no executable found in %s" % args.bindir)
        print("RESULT: passed=0 failed=4")
        return 1

    infos = []
    for path in binaries:
        try:
            infos.append(parse_elf(read(path), path))
        except ElfError as exc:
            print("FAIL A1 %s" % exc)
            print("RESULT: passed=0 failed=4")
            return 1

    print("# smalt HarmonyOS artifact/ABI checks over %d packaged executables"
          % len(infos))
    print("# bindir=%s" % args.bindir)
    passed, failed = [], []

    def report(name, ok, detail):
        (passed if ok else failed).append(name)
        print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))
        sys.stdout.flush()

    # A1 - aarch64 PIE ELF64
    bad = [i["path"] for i in infos
           if i["e_machine"] != EM_AARCH64 or i["e_type"] != ET_DYN]
    report("A1", not bad,
           "all %d binaries are ELF64 LSB PIE (e_type=ET_DYN) with "
           "e_machine=EM_AARCH64(183)%s"
           % (len(infos), "" if not bad else "; wrong: %s" % [os.path.basename(b) for b in bad]))

    # A2 - OHOS musl dynamic loader
    bad = [(os.path.basename(i["path"]), i["interp"]) for i in infos
           if i["interp"] != OHOS_INTERP]
    report("A2", not bad,
           "PT_INTERP is %s for every binary%s"
           % (OHOS_INTERP, "" if not bad else "; got %s" % bad))

    # A3 - only libc.so at runtime (static zlib, musl libm/libpthread stubs)
    problems = []
    for info in infos:
        for lib in info["needed"]:
            if lib.startswith(FORBIDDEN_PREFIXES):
                problems.append("%s needs %s" % (os.path.basename(info["path"]), lib))
        if "libc.so" not in info["needed"]:
            problems.append("%s does not need libc.so (%r)"
                            % (os.path.basename(info["path"]), info["needed"]))
    sample = sorted({lib for i in infos for lib in i["needed"]})
    report("A3", not problems,
           "DT_NEEDED across all binaries is exactly %s - zlib is linked "
           "statically and musl's libm/libpthread archives leave nothing "
           "behind (R26)%s" % (sample, "" if not problems else "; " + "; ".join(problems)))

    # A4 - no build-time RPATH/RUNPATH
    bad = [(os.path.basename(i["path"]), i["rpath"], i["runpath"]) for i in infos
           if i["rpath"] or i["runpath"]]
    report("A4", not bad,
           "no DT_RPATH/DT_RUNPATH in any binary, so the OHOS loader resolves "
           "through system paths only%s" % ("" if not bad else "; got %s" % bad))

    # informational: the hardening posture CI L4 also looks at
    nx = all(i["nx_stack"] is not False for i in infos)
    print("# info: GNU_STACK non-executable for all binaries: %s" % nx)

    print("RESULT: passed=%d failed=%d" % (len(passed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
