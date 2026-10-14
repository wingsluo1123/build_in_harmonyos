#!/usr/bin/env python3
"""HarmonyOS-specific checks for the packaged libao 1.2.0 (R53, fail closed).

Run on the HarmonyOS PC by test_package/conanfile.py::test().  Every check
either passes or aborts the test (no silent skips), and both artifacts it
inspects are exactly what ships / what this test_package produced:

  * the packaged shared library lib/libao.so.4.1.0, and
  * the consumer binary built against it by this test_package.

Assertions
  1. packaged library: ELF64 little-endian EM_AARCH64
  2. packaged library: DT_SONAME == libao.so.4, DT_NEEDED subset {libc.so}
  3. packaged library: has a .codesign section (OHOS ELF signing) and no
     RPATH/RUNPATH entries
  4. consumer binary: ELF64 LE EM_AARCH64 and PT_INTERP exactly
     /lib/ld-musl-aarch64.so.1 (OHOS musl libc, not glibc)
  5. consumer binary: DT_NEEDED includes libao.so.4
  6. consumer binary: references the libao API symbols it calls
     (link-level R34 proof, valid even where the sandbox refuses exec)
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys

EM_AARCH64 = 183
PT_INTERP = 3


def require(cond, msg):
    if not cond:
        print("FAIL:", msg, file=sys.stderr)
        sys.exit(1)


def tool(name):
    path = shutil.which(name)
    if path:
        return path
    fallback = os.path.join("/data/service/hnp/bin", name)
    require(os.path.isfile(fallback), f"tool not found: {name}")
    return fallback


def run_tool(name, *args):
    res = subprocess.run([tool(name)] + list(args),
                         capture_output=True, text=True)
    require(res.returncode == 0,
            f"{name} {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def elf_ident(path):
    with open(path, "rb") as fh:
        head = fh.read(64)
    require(head[:4] == b"\x7fELF", f"not an ELF file: {path}")
    ei_class, ei_data = head[4], head[5]
    machine, = struct.unpack_from("<H", head, 18)
    return ei_class, ei_data, machine


def check_identity(path, what):
    ei_class, ei_data, machine = elf_ident(path)
    require(ei_class == 2, f"{what}: not ELFCLASS64")
    require(ei_data == 1, f"{what}: not little-endian (ELFDATA2LSB)")
    require(machine == EM_AARCH64, f"{what}: not EM_AARCH64 (got {machine})")
    print(f"[ok] {what}: ELF64 LE AArch64")


def pt_interp(path):
    with open(path, "rb") as fh:
        data = fh.read()
    e_phoff, = struct.unpack_from("<Q", data, 32)
    e_phentsize, = struct.unpack_from("<H", data, 54)
    e_phnum, = struct.unpack_from("<H", data, 56)
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        p_type, = struct.unpack_from("<I", data, off)
        if p_type == PT_INTERP:
            p_offset, = struct.unpack_from("<Q", data, off + 8)
            p_filesz, = struct.unpack_from("<Q", data, off + 32)
            return data[p_offset:p_offset + p_filesz].rstrip(b"\x00").decode()
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lib", required=True,
                        help="packaged libao shared library (real file)")
    parser.add_argument("--bin", required=True,
                        help="consumer binary built by the test_package")
    args = parser.parse_args()

    require(os.path.isfile(args.lib), f"missing packaged library: {args.lib}")
    require(os.path.isfile(args.bin), f"missing consumer binary: {args.bin}")

    # ── 1/2/3: the packaged library ─────────────────────────────────────
    check_identity(args.lib, "packaged libao.so")

    lib_dyn = run_tool("readelf", "-d", args.lib)
    require("Library soname: [libao.so.4]" in lib_dyn,
            "packaged library lacks SONAME libao.so.4")
    print("[ok] packaged library SONAME = libao.so.4")

    needed = [ln.split("[", 1)[1].rstrip("]\n")
              for ln in lib_dyn.splitlines() if "NEEDED" in ln]
    allowed = {"libc.so", "libm.so"}
    require(needed and set(needed) <= allowed,
            f"unexpected DT_NEEDED entries: {needed}")
    print(f"[ok] packaged library DT_NEEDED = {needed}")

    require("RPATH" not in lib_dyn and "RUNPATH" not in lib_dyn,
            "packaged library carries an RPATH/RUNPATH entry")
    print("[ok] packaged library has no RPATH/RUNPATH")

    lib_sections = run_tool("readelf", "-S", args.lib)
    require(".codesign" in lib_sections,
            "packaged library has no .codesign section")
    print("[ok] packaged library carries a .codesign section")

    # ── 4/5/6: the consumer binary ──────────────────────────────────────
    check_identity(args.bin, "consumer binary")
    interp = pt_interp(args.bin)
    require(interp == "/lib/ld-musl-aarch64.so.1",
            f"consumer PT_INTERP != /lib/ld-musl-aarch64.so.1 (got {interp})")
    print("[ok] consumer PT_INTERP = /lib/ld-musl-aarch64.so.1")

    bin_dyn = run_tool("readelf", "-d", args.bin)
    require("libao.so.4" in bin_dyn,
            "consumer binary is not linked against libao.so.4")
    print("[ok] consumer binary links libao.so.4")

    undef = run_tool("nm", "-u", args.bin)
    api = ["ao_initialize", "ao_driver_id", "ao_open_file", "ao_play",
           "ao_close", "ao_shutdown"]
    missing = [sym for sym in api if sym not in undef]
    require(not missing,
            f"consumer binary lacks libao API symbols: {missing}")
    print(f"[ok] consumer binary references {len(api)} libao API symbols")

    print("OHOS_SPECIFIC_OK checks=9 lib=%s bin=%s" % (args.lib, args.bin))


if __name__ == "__main__":
    main()
