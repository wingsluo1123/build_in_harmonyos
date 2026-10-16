#!/usr/bin/env python3
"""Consumer checks for the indi-eqmod 1.0-20230126190232 package (OHOS aarch64).

usage: test_eqmod_probe.py <pkg-folder> <libindi-libdir>

Checks — every one inspects the packaged artefacts (nothing is re-implemented,
no upstream tool required, no host execution):
  1. 4 INDI driver executables exist in bin/ and are non-empty ELF64/AArch64
     binaries (e_machine == 183):
       indi_eqmod_telescope / indi_azgti_telescope /
       indi_skyadventurergti_telescope / indi_staradventurer2i_telescope
  2. Each driver's DT_NEEDED is a plain-soname closure that links the INDI
     core runtime (libindidriver.so.2, libindiAlignmentDriver.so.2) and that
     the referenced INDI core libraries really exist in the libindi package
     the closure points at.
  3. share/indi/indi_eqmod.xml registers every packaged driver (device label
     -> driver executable name match), and the companion *-sk.xml INDI
     property skeletons are present and target the EQMod device.

OHOS platform note (E537/R49, same rationale as the approved indi-aok /
indi-shelyak test_package): the host/CI loader cannot map OHOS shared objects
from this filesystem (PROT_EXEC refused, unsigned ELF), so executing the
cross-compiled driver would be refused by the platform, not by the package.
The probe therefore validates the artefacts statically (ELF identity +
DT_NEEDED linkage + XML registration) instead of exec'ing the binaries, so a
platform limitation never masquerades as (or hides) a packaging defect.

Any failing check raises AssertionError -> non-zero exit -> conan test FAIL.
"""
import os
import struct
import sys

EXPECTED_EM_AARCH64 = 0xB7  # 183
DRIVERS = (
    "indi_eqmod_telescope",
    "indi_azgti_telescope",
    "indi_skyadventurergti_telescope",
    "indi_staradventurer2i_telescope",
)
# device label (as registered in share/indi/indi_eqmod.xml) -> driver binary
DEVICE_MAP = {
    "EQMod Mount": "indi_eqmod_telescope",
    "SkyAdventurer GTi": "indi_skyadventurergti_telescope",
    "AZ-GTi Equatorial WiFi": "indi_azgti_telescope",
    "Star Adventurer 2i WiFi": "indi_staradventurer2i_telescope",
}
INDI_CORE_LIBS = ("libindidriver.so.2", "libindiAlignmentDriver.so.2")
COMPANION_XMLS = (
    "indi_eqmod_sk.xml",
    "indi_eqmod_simulator_sk.xml",
    "indi_align_sk.xml",
    "indi_eqmod_scope_limits_sk.xml",
)

assertions = 0
fails = []


def check(cond: bool, name: str) -> None:
    """Record one assertion; fail()es are collected and raised at the end."""
    global assertions
    assertions += 1
    if cond:
        print(f"[ok]   {name}")
    else:
        fails.append(name)
        print(f"[FAIL] {name}")


def check_elf(binpath: str) -> None:
    """Driver exists, non-empty, ELF64, AArch64 (e_machine=183)."""
    name = os.path.basename(binpath)
    check(os.path.isfile(binpath), f"{name}: binary exists in bin/")
    if not os.path.isfile(binpath):
        return
    size = os.path.getsize(binpath)
    check(size >= 4096, f"{name}: non-empty ({size} bytes)")
    with open(binpath, "rb") as fh:
        head = fh.read(64)
    check(head[:4] == b"\x7fELF", f"{name}: ELF magic")
    check(head[4] == 2, f"{name}: ELF64 (EI_CLASS=2)")
    machine = struct.unpack("<H", head[18:20])[0]
    check(machine == EXPECTED_EM_AARCH64,
          f"{name}: e_machine=0x{machine:x} == AArch64 (183)")


def read_needed(binpath: str) -> list:
    """Return DT_NEEDED sonames of an ELF64 little-endian object."""
    with open(binpath, "rb") as fh:
        data = fh.read()
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    loads, dynamic = [], None
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        p_offset = struct.unpack_from("<Q", data, off + 0x08)[0]
        p_vaddr = struct.unpack_from("<Q", data, off + 0x10)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 0x20)[0]
        if p_type == 1:  # PT_LOAD
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:  # PT_DYNAMIC
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        raise ValueError(f"{binpath}: no PT_DYNAMIC segment")

    needed_offsets, strtab_vaddr, strtab_size = [], None, 0
    dyn_off, dyn_size = dynamic
    for idx in range(dyn_size // 16):
        d_tag, d_val = struct.unpack_from("<qQ", data, dyn_off + idx * 16)
        if d_tag == 1:  # DT_NEEDED
            needed_offsets.append(d_val)
        elif d_tag == 5:  # DT_STRTAB
            strtab_vaddr = d_val
        elif d_tag == 10:  # DT_STRSZ
            strtab_size = d_val
    if strtab_vaddr is None:
        raise ValueError(f"{binpath}: no DT_STRTAB entry")

    strtab_off = None
    for vaddr, p_offset, p_filesz in loads:
        if vaddr <= strtab_vaddr < vaddr + p_filesz:
            strtab_off = p_offset + (strtab_vaddr - vaddr)
            break
    if strtab_off is None:
        raise ValueError(f"{binpath}: DT_STRTAB outside PT_LOAD")
    strtab = data[strtab_off:strtab_off + strtab_size]
    names = []
    for name_off in needed_offsets:
        end = strtab.find(b"\0", name_off)
        if end < 0:
            raise ValueError(f"{binpath}: unterminated DT_NEEDED entry")
        names.append(strtab[name_off:end].decode("utf-8", "replace"))
    return names


def check_linkage(binpath: str, indi_libdir: str) -> None:
    """DT_NEEDED must be plain sonames and include the INDI core closure."""
    name = os.path.basename(binpath)
    try:
        needed = read_needed(binpath)
    except Exception as exc:
        check(False, f"{name}: DT_NEEDED parse ({exc})")
        return
    absolute = [n for n in needed if n.startswith("/")]
    check(not absolute,
          f"{name}: DT_NEEDED plain sonames only (no absolute paths)")
    missing = [n for n in INDI_CORE_LIBS if n not in needed]
    check(not missing,
          f"{name}: DT_NEEDED links INDI core {', '.join(INDI_CORE_LIBS)}")
    absent = [n for n in INDI_CORE_LIBS
              if not os.path.isfile(os.path.join(indi_libdir, n))]
    check(not absent,
          f"{name}: INDI core libs present in libindi package "
          f"({', '.join(absent) or 'all found'})")


def check_registration(share_indi: str, bindir: str) -> None:
    """share/indi/indi_eqmod.xml registers all packaged drivers."""
    reg = os.path.join(share_indi, "indi_eqmod.xml")
    check(os.path.isfile(reg), "share/indi/indi_eqmod.xml exists")
    if not os.path.isfile(reg):
        return
    with open(reg, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    for label, driver in DEVICE_MAP.items():
        # device label declared and points at the packaged executable
        check(label in text, f"indi_eqmod.xml declares device '{label}'")
        check(driver in text, f"indi_eqmod.xml references driver {driver}")
        check(os.path.isfile(os.path.join(bindir, driver)),
              f"registered driver {driver} exists in bin/")
    # companion *-sk.xml INDI property skeletons target the EQMod device
    for xml in COMPANION_XMLS:
        path = os.path.join(share_indi, xml)
        check(os.path.isfile(path), f"share/indi/{xml} exists")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                check('device="EQMod Mount"' in fh.read(),
                      f"{xml} targets device 'EQMod Mount'")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    pkg, indi_libdir = sys.argv[1], sys.argv[2]
    bindir = os.path.join(pkg, "bin")
    share_indi = os.path.join(pkg, "share", "indi")

    for driver in DRIVERS:
        check_elf(os.path.join(bindir, driver))
    for driver in DRIVERS:
        check_linkage(os.path.join(bindir, driver), indi_libdir)
    check_registration(share_indi, bindir)

    print(f"assertions={assertions} fails={len(fails)}")
    if fails:
        print("RESULT: FAIL")
        raise AssertionError("indi-eqmod consumer probe failed: "
                             + ", ".join(fails))
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
