#!/usr/bin/env python3
"""indi-shelyak test_package — substantive consumer verification of the packaged
INDI driver executables (R34: real verification, not an empty stub).

The two shipped artifacts (indi_shelyakeshel_spectrograph,
indi_shelyakspox_spectrograph) are OHOS aarch64 command-line drivers that
dynamically link the libindi runtime (libindidriver.so.2,
libindiAlignmentDriver.so.2) plus the OHOS C++ runtime (libc++_shared.so).

Host limitation (documented in libindi/libfli notes, E537/R49): the build host's
HMDFS cannot mmap OHOS shared libraries PROT_EXEC, so the drivers themselves
cannot be executed on the build/CI host (execve returns EPERM — verified:
`timeout 5 $BIN` -> RC=126 "Operation not permitted" even with the full OHOS
SDK C++ lib and libindi package libs on LD_LIBRARY_PATH). This is the same
limitation libindi and libfli document; libfli's test_package likewise verifies
the packaged artifact by parsing it rather than executing it.

Therefore the consumer probe verifies the shipped package substantively:

  1. Both driver executables exist in the package bin/ directory.
  2. Each is a 64-bit AArch64 ELF (ELF64, e_machine = 183) — i.e. a genuine
     HarmonyOS PC arm64 artifact, not a host/x86 or placeholder file.
  3. Each dynamically links the real INDI driver libraries (NEEDED contains
     libindidriver.so.2 / libindiAlignmentDriver.so.2) — proving the declared
     libindi/2.2.2.1 requirement actually reached the link line.
  4. The INDI driver registration file indi_shelyak.xml is installed under the
     package's share/indi/ (drivers.xml lookup dir).
  5. The two drivers register the expected device names (Shelyak eShel /
     Shelyak SPOX) in indi_shelyak.xml.

These checks exercise the delivered package (file existence, ELF identity,
dynamic linkage, registration metadata) and fail loudly if packaging is broken
(e.g. missing binaries, non-arm64 artifacts, dropped libindi linkage).
"""
import os
import re
import struct
import xml.etree.ElementTree as ET


def parse_elf(path):
    """Return (is_elf64, e_machine) from a minimal ELF header parse."""
    with open(path, "rb") as fh:
        ident = fh.read(20)
    if len(ident) < 20 or ident[:4] != b"\x7fELF":
        raise AssertionError(f"{path}: not an ELF file (magic mismatch)")
    elf_class = ident[4]  # 1=ELF32, 2=ELF64
    data = ident[5]       # 1=LSB
    if data != 1:
        raise AssertionError(f"{path}: not little-endian")
    if elf_class == 2:
        with open(path, "rb") as fh:
            fh.seek(18)
            e_machine = struct.unpack("<H", fh.read(2))[0]
        return True, e_machine
    with open(path, "rb") as fh:
        fh.seek(18)
        e_machine = struct.unpack("<H", fh.read(2))[0]
    return False, e_machine


def needed_shared_libs(path):
    """Return the set of DT_NEEDED entries (shared lib names)."""
    with open(path, "rb") as fh:
        ident = fh.read(64)
        if ident[:4] != b"\x7fELF":
            raise AssertionError(f"{path}: not an ELF file")
        elf_class = ident[4]
        # Read e_phoff / e_phentsize / e_phnum
        if elf_class == 2:
            fh.seek(32)
            e_phoff = struct.unpack("<Q", fh.read(8))[0]
            fh.seek(54)
            e_phentsize, e_phnum = struct.unpack("<HH", fh.read(4))
        else:
            fh.seek(28)
            e_phoff = struct.unpack("<I", fh.read(4))[0]
            fh.seek(42)
            e_phentsize, e_phnum = struct.unpack("<HH", fh.read(4))

        dyn_ptrs = []  # (p_offset, p_filesz)
        fh.seek(e_phoff)
        for _ in range(e_phnum):
            ph = fh.read(e_phentsize)
            if len(ph) < e_phentsize:
                break
            p_type = struct.unpack("<I", ph[:4])[0]
            if p_type == 2:  # PT_DYNAMIC
                if elf_class == 2:
                    p_offset = struct.unpack("<Q", ph[8:16])[0]
                    p_filesz = struct.unpack("<Q", ph[32:40])[0]
                else:
                    p_offset = struct.unpack("<I", ph[4:8])[0]
                    p_filesz = struct.unpack("<I", ph[16:20])[0]
                dyn_ptrs.append((p_offset, p_filesz))

        strtab_va = None
        strtab_size = 0
        dyn_strtab_rel = 0  # offset of DT_STRTAB value within its dyn entry
        for offset, filesz in dyn_ptrs:
            fh.seek(offset)
            dyn_data = fh.read(filesz)
            n = filesz // 16
            for i in range(n):
                if elf_class == 2:
                    d_tag = struct.unpack("<q", dyn_data[i * 16:i * 16 + 8])[0]
                    d_val = struct.unpack("<Q", dyn_data[i * 16 + 8:i * 16 + 16])[0]
                else:
                    d_tag = struct.unpack("<i", dyn_data[i * 8:i * 8 + 4])[0]
                    d_val = struct.unpack("<I", dyn_data[i * 8 + 4:i * 8 + 8])[0]
                if d_tag == 5:      # DT_STRTAB
                    strtab_va = d_val
                elif d_tag == 10:   # DT_STRSZ
                    strtab_size = d_val
                elif d_tag == 1:    # DT_NEEDED (first pass, just record)
                    pass
            break  # first PT_DYNAMIC is enough

        if strtab_va is None:
            raise AssertionError(f"{path}: no DT_STRTAB found")

        # Read section headers to map virtual addresses -> file offsets.
        if elf_class == 2:
            fh.seek(40)
            e_shoff = struct.unpack("<Q", fh.read(8))[0]
            fh.seek(58)
            e_shentsize, e_shnum, _ = struct.unpack("<HHH", fh.read(6))
        else:
            fh.seek(32)
            e_shoff = struct.unpack("<I", fh.read(4))[0]
            fh.seek(46)
            e_shentsize, e_shnum, _ = struct.unpack("<HHH", fh.read(6))

        sections = []
        fh.seek(e_shoff)
        for _ in range(e_shnum):
            sh = fh.read(e_shentsize)
            if len(sh) < e_shentsize:
                break
            if elf_class == 2:
                sh_addr = struct.unpack("<Q", sh[16:24])[0]
                sh_offset = struct.unpack("<Q", sh[24:32])[0]
                sh_size = struct.unpack("<Q", sh[32:40])[0]
            else:
                sh_addr = struct.unpack("<I", sh[12:16])[0]
                sh_offset = struct.unpack("<I", sh[16:20])[0]
                sh_size = struct.unpack("<I", sh[20:24])[0]
            sections.append((sh_addr, sh_offset, sh_size))

        def vaddr_to_file(vaddr):
            for addr, off, size in sections:
                if addr <= vaddr < addr + size:
                    return off + (vaddr - addr)
            return None

        strtab_off = vaddr_to_file(strtab_va)
        if strtab_off is None:
            raise AssertionError(f"{path}: cannot map strtab vaddr to file")
        fh.seek(strtab_off)
        strtab = fh.read(strtab_size) if strtab_size else b""

        needed = set()
        for offset, filesz in dyn_ptrs:
            fh.seek(offset)
            dyn_data = fh.read(filesz)
            n = filesz // 16
            for i in range(n):
                if elf_class == 2:
                    d_tag = struct.unpack("<q", dyn_data[i * 16:i * 16 + 8])[0]
                    d_val = struct.unpack("<Q", dyn_data[i * 16 + 8:i * 16 + 16])[0]
                else:
                    d_tag = struct.unpack("<i", dyn_data[i * 8:i * 8 + 4])[0]
                    d_val = struct.unpack("<I", dyn_data[i * 8 + 4:i * 8 + 8])[0]
                if d_tag == 1:  # DT_NEEDED
                    # d_val is a byte offset into the .dynstr string table,
                    # not a virtual address.
                    idx = d_val
                    end = strtab.find(b"\x00", idx)
                    if end != -1:
                        needed.add(strtab[idx:end].decode("utf-8", "replace"))
        return needed


def main():
    failures = []
    checks = []

    def check(name, cond, detail=""):
        if cond:
            checks.append(f"ok   - {name} {detail}".strip())
        else:
            failures.append(f"FAIL - {name} {detail}".strip())
            checks.append(f"FAIL - {name} {detail}".strip())

    # Locate the installed package folder (path provided by the caller).
    pkg_dir = os.environ.get("SHELYAK_PKG_DIR")
    if not pkg_dir or not os.path.isdir(pkg_dir):
        raise AssertionError("SHELYAK_PKG_DIR must point at the installed "
                             "indi-shelyak package folder")
    bin_dir = os.path.join(pkg_dir, "bin")
    share_dir = os.path.join(pkg_dir, "share", "indi")

    drivers = ["indi_shelyakeshel_spectrograph", "indi_shelyakspox_spectrograph"]
    for name in drivers:
        path = os.path.join(bin_dir, name)
        check(f"binary exists: {name}", os.path.isfile(path))
        if not os.path.isfile(path):
            continue
        is_elf64, machine = parse_elf(path)
        check(f"{name} is ELF64", is_elf64)
        check(f"{name} machine=AArch64", machine == 183,
              f"(e_machine={machine})")
        needed = needed_shared_libs(path)
        check(f"{name} links libindidriver",
              "libindidriver.so.2" in needed,
              f"(NEEDED={sorted(needed)})")
        check(f"{name} links libindiAlignmentDriver",
              "libindiAlignmentDriver.so.2" in needed)
        check(f"{name} links libc++_shared (OHOS runtime)",
              "libc++_shared.so" in needed)

    # INDI driver registration file.
    xml_path = os.path.join(share_dir, "indi_shelyak.xml")
    check("indi_shelyak.xml installed", os.path.isfile(xml_path))
    if os.path.isfile(xml_path):
        try:
            root = ET.parse(xml_path).getroot()
            xml_text = ET.tostring(root, encoding="unicode")
            check("registers 'Shelyak eShel'", "Shelyak eShel" in xml_text)
            check("registers 'Shelyak SPOX'", "Shelyak SPOX" in xml_text)
            check("driver eshel registered",
                  "indi_shelyakeshel_spectrograph" in xml_text)
            check("driver spox registered",
                  "indi_shelyakspox_spectrograph" in xml_text)
        except ET.ParseError as exc:
            check("indi_shelyak.xml parses as XML", False, f"({exc})")

    print("== indi-shelyak consumer probe ==")
    for line in checks:
        print(line)
    total = len(checks)
    failed = len(failures)
    print(f"== {total} checks, {failed} failures ==")
    if failed:
        raise AssertionError(f"{failed} of {total} checks failed")
    print("RESULT: PASSED")


if __name__ == "__main__":
    main()
