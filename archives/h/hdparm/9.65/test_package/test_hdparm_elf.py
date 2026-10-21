#!/usr/bin/env python3
"""HarmonyOS ELF loading-contract consumer test for hdparm/9.65.

Why this file exists
--------------------
CI L0c (`no_test_sources`) requires a real test source inside `test_package/`
with one of the suffixes .c/.cpp/.cc/.cxx/.sh/.py. hdparm is a plain CLI
application, so a consumer cannot link a library API; and the HarmonyOS build
host refuses to execute unsigned ELF files ("Operation not permitted"), so the
tool itself cannot be run here.

What a consumer actually needs on HarmonyOS PC is a *loadable* binary, so this
test parses the packaged artifact and asserts its loading contract:

  1. ELF64 little-endian AArch64 header
  2. PT_INTERP == /lib/ld-musl-aarch64.so.1   (musl dynamic loader)
  3. DT_NEEDED contains libc.so               (resolvable against OHOS sysroot)
  4. a .note.ohos.ident section               (built for HarmonyOS, not glibc)

Usage: test_hdparm_elf.py <path-to-installed-hdparm>
Exit code 0 = all contract assertions passed, 1 = contract violated.
"""
import struct
import sys

EM_AARCH64 = 183
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
EXPECTED_INTERP = "/lib/ld-musl-aarch64.so.1"
REQUIRED_SONAME_PREFIX = "libc.so"
REQUIRED_NOTE = ".note.ohos.ident"


def parse(path):
    """Return a dict with the fields this contract cares about."""
    with open(path, "rb") as fh:
        data = fh.read()

    assert data[:4] == b"\x7fELF", "not an ELF file: %r" % (data[:4],)
    assert data[4] == 2 and data[5] == 1, "expected ELF64 little-endian"
    (e_machine,) = struct.unpack_from("<H", data, 18)
    (e_phoff,) = struct.unpack_from("<Q", data, 32)
    (e_shoff,) = struct.unpack_from("<Q", data, 40)
    (e_phentsize, e_phnum) = struct.unpack_from("<HH", data, 54)
    (e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHH", data, 58)

    # Program headers: locate PT_INTERP / PT_DYNAMIC and the LOAD segments
    # used to translate virtual addresses into file offsets.
    interp = None
    dynamic_seg = None
    loads = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        (p_type, _flags, p_offset, p_vaddr, _paddr,
         p_filesz, _memsz, _align) = struct.unpack_from("<IIQQQQQQ", data, off)
        if p_type == PT_INTERP:
            interp = data[p_offset:p_offset + p_filesz].split(b"\0")[0].decode()
        elif p_type == PT_DYNAMIC:
            dynamic_seg = (p_offset, p_filesz)
        elif p_type == PT_LOAD:
            loads.append((p_vaddr, p_vaddr + p_filesz, p_offset))

    needed = []
    if dynamic_seg:
        strtab_addr = None
        entries = []
        off, size = dynamic_seg
        for i in range(size // 16):
            d_tag, d_val = struct.unpack_from("<qQ", data, off + i * 16)
            if d_tag == DT_NULL:
                break
            entries.append((d_tag, d_val))
            if d_tag == DT_STRTAB:
                strtab_addr = d_val
        strtab_off = None
        if strtab_addr is not None:
            for vaddr, vend, p_offset in loads:
                if vaddr <= strtab_addr < vend:
                    strtab_off = p_offset + (strtab_addr - vaddr)
                    break
        if strtab_off is not None:
            for d_tag, d_val in entries:
                if d_tag != DT_NEEDED:
                    continue
                start = strtab_off + d_val
                end = data.index(b"\0", start)
                needed.append(data[start:end].decode())

    # Section names (for the HarmonyOS note section).
    sections = []
    if e_shoff and e_shnum:
        shstr_off = None
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            (sh_name, sh_type, _flags, _addr, sh_offset, sh_size) = \
                struct.unpack_from("<IIQQQQ", data, off)
            if i == e_shstrndx:
                shstr_off = sh_offset
            sections.append([sh_name, sh_type, sh_offset, sh_size])
        if shstr_off is not None:
            for sec in sections:
                start = shstr_off + sec[0]
                sec[0] = data[start:data.index(b"\0", start)].decode()

    return {
        "machine": e_machine,
        "interp": interp,
        "needed": needed,
        "sections": [s[0] for s in sections],
    }


def main():
    if len(sys.argv) != 2:
        print("usage: test_hdparm_elf.py <path-to-hdparm>")
        return 2
    path = sys.argv[1]
    info = parse(path)

    print("[ohos-contract] binary         : %s" % path)
    print("[ohos-contract] e_machine      : %d (AArch64=%d)"
          % (info["machine"], EM_AARCH64))
    print("[ohos-contract] PT_INTERP      : %s" % info["interp"])
    print("[ohos-contract] DT_NEEDED      : %s" % ", ".join(info["needed"]))
    print("[ohos-contract] note sections  : %s"
          % ", ".join(s for s in info["sections"] if s.startswith(".note")))

    assert info["machine"] == EM_AARCH64, \
        "e_machine=%d, expected AArch64 (%d)" % (info["machine"], EM_AARCH64)
    assert info["interp"] == EXPECTED_INTERP, \
        "PT_INTERP=%r, expected %r" % (info["interp"], EXPECTED_INTERP)
    assert any(n.startswith(REQUIRED_SONAME_PREFIX) for n in info["needed"]), \
        "DT_NEEDED has no %s: %s" % (REQUIRED_SONAME_PREFIX, info["needed"])
    assert REQUIRED_NOTE in info["sections"], \
        "%s section missing (not a HarmonyOS build): %s" % (
            REQUIRED_NOTE, info["sections"])

    print("[ohos-contract] PASS: ELF loading contract satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
