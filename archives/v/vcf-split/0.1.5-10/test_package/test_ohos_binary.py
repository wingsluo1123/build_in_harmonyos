#!/usr/bin/env python3
"""OHOS platform conformance checks for the installed vcf-split binary.

The vcf-split package is an OHOS/aarch64 executable, so beyond functional
behaviour it must carry the platform properties OHOS requires: it has to be an
AArch64 position-independent executable tagged with the OHOS identification
note, with a non-executable stack and full RELRO.

The ELF is parsed in pure Python (no readelf dependency), so this check also
works in stripped-down test environments.
"""

import os
import struct
import sys
from pathlib import Path

ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_DYN = 3
EM_AARCH64 = 0xB7
OHOS_NOTE_SECTION = ".note.ohos.ident"

PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
PF_X = 0x1
DF_BIND_NOW = 0x8
DF_1_PIE = 0x08000000


def parse_elf(path):
    """Return the ELF bits this check needs, or raise AssertionError."""
    data = path.read_bytes()
    if data[:4] != ELF_MAGIC:
        raise AssertionError(f"{path.name}: not an ELF file")

    ei_class, ei_data = data[4], data[5]
    if ei_class != ELFCLASS64:
        raise AssertionError(f"{path.name}: not a 64-bit ELF (ei_class={ei_class})")
    if ei_data != ELFDATA2LSB:
        raise AssertionError(f"{path.name}: not little-endian (ei_data={ei_data})")

    e_type, e_machine = struct.unpack_from("<HH", data, 0x10)
    e_phoff, e_shoff = struct.unpack_from("<QQ", data, 0x20)
    e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(
        "<HHHHH", data, 0x36
    )

    section_names = []
    if e_shoff and e_shnum:
        strtab_hdr = e_shoff + e_shstrndx * e_shentsize
        strtab_off, strtab_size = struct.unpack_from("<QQ", data, strtab_hdr + 0x18)
        strtab = data[strtab_off:strtab_off + strtab_size]
        for index in range(e_shnum):
            header = e_shoff + index * e_shentsize
            name_off = struct.unpack_from("<I", data, header)[0]
            end = strtab.find(b"\0", name_off)
            section_names.append(strtab[name_off:end].decode("ascii", "replace"))

    segments = {}
    for index in range(e_phnum):
        header = e_phoff + index * e_phentsize
        p_type, p_flags = struct.unpack_from("<II", data, header)
        segments.setdefault(p_type, []).append(p_flags)

    dynamic_flags = 0
    dynamic_flags_1 = 0
    for index in range(e_shnum):
        header = e_shoff + index * e_shentsize
        if section_names[index] != ".dynamic":
            continue
        # ELF64 section header: sh_offset@0x18, sh_size@0x20, sh_entsize@0x38
        offset, size = struct.unpack_from("<QQ", data, header + 0x18)
        entsize = struct.unpack_from("<Q", data, header + 0x38)[0] or 16
        for entry in range(offset, offset + size, entsize):
            tag, value = struct.unpack_from("<QQ", data, entry)
            if tag == 0:
                break
            if tag == 30:  # DT_FLAGS
                dynamic_flags = value
            elif tag == 0x6FFFFFFB:  # DT_FLAGS_1
                dynamic_flags_1 = value

    return {
        "e_type": e_type,
        "e_machine": e_machine,
        "section_names": section_names,
        "segments": segments,
        "dynamic_flags": dynamic_flags,
        "dynamic_flags_1": dynamic_flags_1,
    }


def main(package_dir):
    if os.name == "nt":
        raise RuntimeError("vcf-split OHOS package targets POSIX platforms only")

    exe = Path(package_dir) / "bin" / "vcf-split"
    if not exe.is_file():
        raise FileNotFoundError(exe)

    elf = parse_elf(exe)
    assertions = 0

    if elf["e_machine"] != EM_AARCH64:
        raise AssertionError(f"e_machine={elf['e_machine']:#x}, expected AArch64 ({EM_AARCH64:#x})")
    assertions += 1

    if elf["e_type"] != ET_DYN:
        raise AssertionError(f"e_type={elf['e_type']}, expected ET_DYN (position-independent executable)")
    assertions += 1

    if OHOS_NOTE_SECTION not in elf["section_names"]:
        raise AssertionError(f"missing {OHOS_NOTE_SECTION}: binary is not tagged as an OHOS executable")
    assertions += 1

    stack_flags = elf["segments"].get(PT_GNU_STACK)
    if not stack_flags:
        raise AssertionError("missing PT_GNU_STACK segment")
    if stack_flags[0] & PF_X:
        raise AssertionError("GNU_STACK is executable (NX is not enforced)")
    assertions += 1

    if PT_GNU_RELRO not in elf["segments"]:
        raise AssertionError("missing PT_GNU_RELRO: no RELRO hardening")
    assertions += 1

    if not elf["dynamic_flags"] & DF_BIND_NOW:
        raise AssertionError("DT_FLAGS lacks DF_BIND_NOW: RELRO is not full")
    assertions += 1

    if not elf["dynamic_flags_1"] & DF_1_PIE:
        raise AssertionError("DT_FLAGS_1 lacks DF_1_PIE")
    assertions += 1

    print(
        f"vcf-split OHOS platform conformance: {assertions} assertions passed "
        f"(AArch64 PIE, {OHOS_NOTE_SECTION}, NX stack, full RELRO)"
    )
    return assertions


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_ohos_binary.py <package-folder>")
    main(sys.argv[1])
