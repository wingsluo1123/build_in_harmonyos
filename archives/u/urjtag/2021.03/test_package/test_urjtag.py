#!/usr/bin/env python3
"""Consumer + HarmonyOS platform verification of packaged urjtag 2021.03.

    test_urjtag.py --jtag <jtag cmd...> --bsdl2jtag <bsdl2jtag cmd...>
                   [--pkgroot <package root>]

Checks:
  1. jtag command-line contract (--version / --help, exit codes)
  2. a real JTAG-script run: `jtag -n script` executes `help` + `quit`
     through the packaged command parser/dispatch loop (no hardware);
     the command list must contain the statically linked `svf` and `bsdl`
     command modules
  3. bsdl2jtag usage contract (wrong argc -> usage + exit 1)
  4. HarmonyOS ELF checks on jtag: aarch64 PIE, OHOS musl loader (both
     coexisting loader names accepted, glibc loader rejected), DT_NEEDED
     wiring (OHOS libc.so, libusb-1.0.so; no glibc-only sonames, no
     absolute paths)
  5. the packaged static library liburjtag.a (ar archive, non-empty)
  6. public headers + flash part database installed for consumers
"""

import os
import struct
import subprocess
import sys
import tempfile

EM_AARCH64 = 183
ET_DYN = 3
PT_INTERP = 3
PT_DYNAMIC = 2
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_SONAME = 14

# OHOS ships both loader names and they coexist on the device; a glibc
# aarch64 build would ask for /lib64/ld-linux-aarch64.so.2 instead.
OHOS_LOADERS = (b"/lib/ld-musl-aarch64.so.1", b"/lib/ld-linux-aarch64.so.1")
GLIBC_LOADER = b"/lib64/ld-linux-aarch64.so.2"
# glibc-specific sonames that must not appear in DT_NEEDED of an OHOS binary
GLIBC_ONLY = ("libc.so.6", "libpthread.so", "libdl.so", "librt.so")

# Host-visible guest rootfs (cross-build machine only; on a real OHOS device
# this directory does not exist and the shim list stays empty).
GUEST_LIB = "/opt/ohos-guest/lib"
SHIM_NAMES = (
    "libfdchkshim.so",
    "libchkfcnshim.so",
    "libmemchrchkshim.so",
    "libpcmchkshim.so",
    "libmprotshim.so",
    "libmallinfo2shim.so",
    "libarc4shim.so",
)

results = []


def split_commands(argv):
    commands = {}
    key = None
    for token in argv:
        if token in ("--jtag", "--bsdl2jtag", "--pkgroot"):
            key = token[2:]
            commands[key] = []
        elif key is not None:
            commands[key].append(token)
    return commands


ARGS = split_commands(sys.argv[1:])
JTAG = ARGS.get("jtag") or []
BSDL2JTAG = ARGS.get("bsdl2jtag") or []
PKGROOT = (ARGS.get("pkgroot") or [None])[0]
if not JTAG or not BSDL2JTAG:
    sys.exit("usage: test_urjtag.py --jtag <cmd> --bsdl2jtag <cmd> [--pkgroot <dir>]")


def check(condition, message):
    if not condition:
        print(f"FAIL: {message}")
        sys.exit(1)
    results.append(message)
    print(f"ok: {message}")


def _shims_preload():
    if not os.path.isdir(GUEST_LIB):
        return ""
    existing = [
        os.path.join(GUEST_LIB, name)
        for name in SHIM_NAMES
        if os.path.isfile(os.path.join(GUEST_LIB, name))
    ]
    return ":".join(existing)


def run(cmd):
    """Run a packaged-binary command, injecting the guest shims if present."""
    env = dict(os.environ)
    preload = _shims_preload()
    if preload:
        env["LD_PRELOAD"] = (
            preload + ":" + env["LD_PRELOAD"]
            if env.get("LD_PRELOAD")
            else preload
        )
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)


def parse_elf64(path):
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:4] != b"\x7fELF":
        raise ValueError(f"{path}: not an ELF file")
    if blob[4] != 2:
        raise ValueError(f"{path}: not a 64-bit ELF")
    e_type, e_machine = struct.unpack_from("<HH", blob, 16)
    (e_phoff,) = struct.unpack_from("<Q", blob, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 54)
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags = struct.unpack_from("<II", blob, off)
        p_offset, p_vaddr = struct.unpack_from("<QQ", blob, off + 8)
        phdrs.append((p_type, p_flags, p_offset, p_vaddr))
    return blob, e_type, e_machine, phdrs


def dynamic_entries(blob, phdrs):
    dyn = None
    for p_type, _flags, p_offset, _vaddr in phdrs:
        if p_type == PT_DYNAMIC:
            dyn = p_offset
            break
    if dyn is None:
        return None, []
    entries = []
    count = 0
    while True:
        tag, value = struct.unpack_from("<qQ", blob, dyn + count * 16)
        if tag == DT_NULL:
            break
        entries.append((tag, value))
        count += 1
        if count > 4096:
            raise ValueError("DT_NULL not found")
    strtab = None
    for tag, value in entries:
        if tag == DT_STRTAB:
            strtab = value
            break
    if strtab is None:
        return None, []
    soname, needed = None, []
    for tag, value in entries:
        if tag == DT_SONAME:
            end = blob.index(b"\x00", strtab + value)
            soname = blob[strtab + value : end].decode()
        elif tag == DT_NEEDED:
            end = blob.index(b"\x00", strtab + value)
            needed.append(blob[strtab + value : end].decode())
    return soname, needed


def _first_elf_member(ar_blob):
    """Return the 20-byte ELF header of the first ELF object in an ar archive
    (skipping the '/' symbol-table and '//' long-name members), or None."""
    off = 8
    while off + 60 <= len(ar_blob):
        header = ar_blob[off : off + 60]
        try:
            size = int(header[48:58].decode("ascii").strip() or "0")
        except ValueError:
            return None
        data_off = off + 60
        if ar_blob[data_off : data_off + 4] == b"\x7fELF":
            return ar_blob[data_off : data_off + 20]
        off = data_off + size + (size % 2)
    return None


def main():
    # --- 1. jtag command-line contract --------------------------------------
    proc = run(JTAG + ["--version"])
    check(proc.returncode == 0, "jtag --version exits 0")
    check("UrJTAG 2021.03" in proc.stdout, "jtag --version reports 'UrJTAG 2021.03'")
    first_version_output = proc.stdout

    proc = run(JTAG + ["--help"])
    check(proc.returncode == 0, "jtag --help exits 0")
    check("Usage: jtag [OPTIONS]" in proc.stdout, "jtag --help prints usage header")
    check("-v, --version" in proc.stdout, "jtag --help lists the version option")
    check(
        "file containing commands to execute" in proc.stdout,
        "jtag --help documents the [FILE] positional JTAG script argument",
    )

    # --- 2. real JTAG-script run through the command parser -----------------
    script = tempfile.NamedTemporaryFile("w", suffix=".jtc", delete=False)
    script.write("help\nquit\n")
    script.close()
    try:
        proc = run(JTAG + ["-n", script.name])
        check(
            proc.returncode == 0,
            "jtag executes a JTAG script ([FILE] arg, --norc) to completion",
        )
        check(
            "Command list:" in proc.stdout,
            "command dispatcher answers 'help' with the command list",
        )
        check("quit" in proc.stdout, "command list contains the quit command")
        check(
            "execute svf commands from file" in proc.stdout,
            "command list contains the svf command (SVF player statically linked)",
        )
        check(
            "manage BSDL files" in proc.stdout,
            "command list contains the bsdl command (BSDL module statically linked)",
        )
        check(
            'Type "help COMMAND" for details' in proc.stdout,
            "help footer instructs per-command help",
        )
    finally:
        os.unlink(script.name)

    # --- 3. bsdl2jtag usage contract ----------------------------------------
    proc = run(BSDL2JTAG)
    check(proc.returncode == 1, "bsdl2jtag with no args exits 1")
    check(
        "bsdl2jtag <bsdl-file> <jtag-file>" in proc.stdout,
        "bsdl2jtag prints its usage on wrong argc",
    )

    # --- 4. HarmonyOS ELF checks on the jtag binary -------------------------
    jtag_path = JTAG[-1]
    check(os.path.isfile(jtag_path), "packaged jtag binary exists")
    blob, e_type, e_machine, phdrs = parse_elf64(jtag_path)
    check(e_machine == EM_AARCH64, "jtag is an aarch64 ELF (EM_AARCH64)")
    check(e_type == ET_DYN, "jtag is a PIE (ET_DYN)")

    interp = None
    for p_type, _flags, p_offset, _vaddr in phdrs:
        if p_type == PT_INTERP:
            end = blob.index(b"\x00", p_offset)
            interp = blob[p_offset:end]
    check(
        interp in OHOS_LOADERS,
        f"jtag interpreter is an OHOS musl loader ({interp!r})",
    )
    check(
        interp != GLIBC_LOADER,
        "jtag interpreter is not the glibc aarch64 loader",
    )

    _soname, needed = dynamic_entries(blob, phdrs)
    check("libc.so" in needed, "jtag DT_NEEDED contains the OHOS libc.so")
    check(
        any(n.startswith("libusb-1.0.so") for n in needed),
        "jtag DT_NEEDED links libusb-1.0 (USB JTAG cable support)",
    )
    check(
        not any(n in GLIBC_ONLY for n in needed),
        "jtag DT_NEEDED has no glibc-only sonames",
    )
    check(
        not any(n.startswith("/") for n in needed),
        "jtag DT_NEEDED has no absolute paths",
    )

    # --- 5. packaged static library --------------------------------------------
    if PKGROOT:
        libdir = os.path.join(PKGROOT, "lib")
        static_lib = os.path.join(libdir, "liburjtag.a")
        check(os.path.isfile(static_lib), "liburjtag.a static library is packaged in lib/")
        with open(static_lib, "rb") as handle:
            ar_blob = handle.read()
        check(
            ar_blob[:8] == b"!<arch>\n",
            "liburjtag.a has the ar archive magic",
        )
        first_obj = _first_elf_member(ar_blob)
        check(
            first_obj is not None
            and first_obj[18:20] == struct.pack("<H", EM_AARCH64),
            "liburjtag.a contains an aarch64 ELF object member",
        )

    # --- 6. consumer-facing headers + flash part database --------------------
    if PKGROOT:
        check(
            os.path.isfile(os.path.join(PKGROOT, "include", "urjtag", "urjtag.h")),
            "public header include/urjtag/urjtag.h installed",
        )
        check(
            os.path.isfile(os.path.join(PKGROOT, "include", "urjtag", "cmd.h")),
            "public header include/urjtag/cmd.h installed",
        )
        share = os.path.join(PKGROOT, "share")
        manufacturers = []
        for root, _dirs, files in os.walk(share):
            if "MANUFACTURERS" in files:
                manufacturers.append(os.path.join(root, "MANUFACTURERS"))
        check(
            bool(manufacturers),
            "flash part database (share/.../MANUFACTURERS) installed",
        )

    # --- 7. determinism -------------------------------------------------------
    proc = run(JTAG + ["--version"])
    check(proc.stdout == first_version_output, "jtag --version output is deterministic")

    print(f"\n{len(results)} assertions passed")


if __name__ == "__main__":
    main()
