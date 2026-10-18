#!/usr/bin/env python3
"""test_package -- krunner 6.28.0 OHOS-specific artefact checks.

test_krunner (the consumer program) covers behaviour. This script
covers the *build products*, i.e. the things that only exist because of the
OHOS adaptations in conanfile.py:

  * ``lib/libKF6Runner.so`` must be the only ``libKF6Runner.so*``
    entry and must be a regular file -- no ``.so.6`` / ``.so.6.28.0`` / dev
    symlink. OHOS /storage forbids symlinks (a versioned SOVERSION chain
    dies with EPERM, device-proven; kscreenlocker 6.7.2 precedent), so the
    recipe sets no CMAKE_SHARED_LIBRARY_SONAME flags and the build emits a
    single unversioned shared object (kpackage/6.26.0.1 precedent).
  * the file must be an AArch64, little-endian, ELF64 shared object --
    the build really targeted OHOS aarch64 rather than the host.
  * its DT_SONAME must be exactly ``libKF6Runner.so`` (patch 0002
    passes ``-Wl,-soname,libKF6Runner.so`` explicitly where the
    platform module defines no soname flag).
  * every DT_NEEDED entry must be a bare basename (no path separator):
    patch 0002 links the KF6 dependencies by exact-file-name
    -l:libKF6*.so flags (the KF6:: targets are dropped from the link
    interface), so the linker records basenames instead of machine-private
    Conan cache paths (non-relocatable, E537).
  * the ``.codesign`` section must be present, because package() re-signs
    every installed ELF: CMake rewrites the RUNPATH on install, which
    invalidates the OHOS build-time signature and makes the loader refuse the
    library with "Permission denied".

Only structured ELF header / section-table / dynamic-section reads are used
-- the file is never grepped for byte patterns.

Usage: test_krunner_elf.py <package_folder>
"""
import os
import struct
import sys

ELF_MAGIC = b"\x7fELF"
EI_CLASS = 4
EI_DATA = 5
EI_VERSION = 6
E_TYPE_OFFSET = 16
E_PHOFF_OFFSET = 32
E_PHENTSIZE_OFFSET = 54
E_PHNUM_OFFSET = 56
E_SHOFF_OFFSET = 40
E_SHENTSIZE_OFFSET = 58
E_SHNUM_OFFSET = 60
E_SHSTRNDX_OFFSET = 62
SH_OFFSET_OFFSET = 24
SH_NAME_OFFSET = 0

ELFCLASS64 = 2
ELFDATA2LSB = 1
EV_CURRENT = 1
ET_DYN = 3
EM_AARCH64 = 183

PT_LOAD = 1
PT_DYNAMIC = 2
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_SONAME = 14

SHARED_OBJECT = "libKF6Runner.so"


def is_regular_file(path):
    """Regular-file check that rejects a symlinked final component.

    os.path.isfile() follows symlinks, so a link named exactly
    libKF6Runner.so would satisfy the "single regular file, no
    symlink" invariant of this script while pointing anywhere.  OHOS
    /storage forbids symlinks altogether, so this only tightens the
    check; a symlinked install must not be reported as PASS.
    """
    return os.path.isfile(path) and not os.path.islink(path)


def section_names(data):
    """Return the section names of an ELF64 image (empty if unparseable)."""
    e_shoff, = struct.unpack_from("<Q", data, E_SHOFF_OFFSET)
    e_shentsize, = struct.unpack_from("<H", data, E_SHENTSIZE_OFFSET)
    e_shnum, = struct.unpack_from("<H", data, E_SHNUM_OFFSET)
    e_shstrndx, = struct.unpack_from("<H", data, E_SHSTRNDX_OFFSET)
    if not e_shoff or not e_shnum or e_shstrndx >= e_shnum:
        return []
    strtab, = struct.unpack_from(
        "<Q", data, e_shoff + e_shstrndx * e_shentsize + SH_OFFSET_OFFSET
    )
    names = []
    for index in range(e_shnum):
        name_off, = struct.unpack_from(
            "<I", data, e_shoff + index * e_shentsize + SH_NAME_OFFSET
        )
        start = strtab + name_off
        end = data.find(b"\x00", start)
        if end < 0:
            return []
        names.append(data[start:end].decode("latin-1"))
    return names


def vaddr_to_offset(loads, vaddr):
    """Map a virtual address to a file offset via the PT_LOAD table."""
    for seg_vaddr, seg_off, seg_size in loads:
        if seg_vaddr <= vaddr < seg_vaddr + seg_size:
            return seg_off + (vaddr - seg_vaddr)
    return None


def dyn_strings(data):
    """Read DT_STRTAB/DT_SONAME/DT_NEEDED from PT_DYNAMIC.

    DT_STRTAB is a virtual address; it is mapped through the PT_LOAD
    table (a segment whose p_vaddr differs from its p_offset would
    otherwise make every string read land on the wrong bytes). When the
    mapping fails, the .dynstr section offset is used instead. Returns
    (soname, [needed, ...]) or (None, []) when the dynamic section
    cannot be located.
    """
    e_phoff, = struct.unpack_from("<Q", data, E_PHOFF_OFFSET)
    e_phentsize, = struct.unpack_from("<H", data, E_PHENTSIZE_OFFSET)
    e_phnum, = struct.unpack_from("<H", data, E_PHNUM_OFFSET)
    dyn_off = None
    loads = []
    # Scan every program header (PT_LOAD segments are not guaranteed to
    # precede PT_DYNAMIC, so no early exit) collecting the load table.
    for index in range(e_phnum):
        entry = e_phoff + index * e_phentsize
        p_type, = struct.unpack_from("<I", data, entry)
        if p_type == PT_LOAD:
            p_offset, = struct.unpack_from("<Q", data, entry + 8)
            p_vaddr, = struct.unpack_from("<Q", data, entry + 16)
            p_filesz, = struct.unpack_from("<Q", data, entry + 32)
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == PT_DYNAMIC:
            dyn_off, = struct.unpack_from("<Q", data, entry + 8)
    if dyn_off is None:
        return None, []
    strtab = None
    soname_val = None
    needed = []
    for step in range(4096):
        tag, val = struct.unpack_from("<qQ", data, dyn_off + step * 16)
        if tag == DT_NULL:
            break
        if tag == DT_STRTAB:
            # d_ptr is a virtual address -- map it before use; None
            # falls through to the .dynstr section-offset fallback.
            strtab = vaddr_to_offset(loads, val)
        elif tag == DT_SONAME:
            soname_val = val
        elif tag == DT_NEEDED:
            needed.append(val)
    if strtab is None:
        # fall back to the .dynstr section offset
        e_shoff, = struct.unpack_from("<Q", data, E_SHOFF_OFFSET)
        e_shentsize, = struct.unpack_from("<H", data, E_SHENTSIZE_OFFSET)
        e_shnum, = struct.unpack_from("<H", data, E_SHNUM_OFFSET)
        for name, offset in zip(
            section_names(data),
            (
                struct.unpack_from(
                    "<Q", data, e_shoff + i * e_shentsize + SH_OFFSET_OFFSET
                )[0]
                for i in range(e_shnum)
            ),
        ):
            if name == ".dynstr":
                strtab = offset
                break
    if strtab is None:
        return None, []

    def read_string(offset):
        end = data.find(b"\x00", strtab + offset)
        if end < 0:
            return ""
        return data[strtab + offset : end].decode("latin-1")

    soname = read_string(soname_val) if soname_val is not None else None
    return soname, [read_string(off) for off in needed]


def main():
    if len(sys.argv) > 1:
        package_folder = sys.argv[1]
    else:
        package_folder = os.environ.get("PACKAGE_FOLDER", "")
    if not package_folder:
        print("FAIL: no package folder given")
        return 1

    libdir = os.path.join(package_folder, "lib")
    problems = []
    checks = 0

    # --- installed objects: single unversioned file, no SONAME links ------
    present = sorted(
        name
        for name in (os.listdir(libdir) if os.path.isdir(libdir) else [])
        if name.startswith("libKF6Runner.so")
    )
    checks += 1
    if present != [SHARED_OBJECT]:
        problems.append(
            "expected exactly [%s] in lib/, found %r" % (SHARED_OBJECT, present)
        )
    shared_path = os.path.join(libdir, SHARED_OBJECT)
    regular = is_regular_file(shared_path)
    checks += 1
    if not regular:
        problems.append(
            "%s is not a regular file (missing or a symlink)" % SHARED_OBJECT
        )

    if not regular:
        names = []
    else:
        path = shared_path
        with open(path, "rb") as handle:
            data = handle.read()

        # --- ELF identification ------------------------------------------
        checks += 1
        if data[:4] != ELF_MAGIC:
            problems.append("%s: not an ELF file" % SHARED_OBJECT)
            names = []
        else:
            names = None
            for label, offset, expected in (
                ("EI_CLASS is not ELFCLASS64", EI_CLASS, ELFCLASS64),
                ("EI_DATA is not ELFDATA2LSB", EI_DATA, ELFDATA2LSB),
                ("EI_VERSION is not EV_CURRENT", EI_VERSION, EV_CURRENT),
            ):
                checks += 1
                if data[offset] != expected:
                    problems.append("%s: %s" % (SHARED_OBJECT, label))

            e_type, e_machine = struct.unpack_from("<HH", data, E_TYPE_OFFSET)
            checks += 1
            if e_type != ET_DYN:
                problems.append(
                    "%s: e_type=%d, expected ET_DYN" % (SHARED_OBJECT, e_type)
                )
            checks += 1
            if e_machine != EM_AARCH64:
                problems.append(
                    "%s: e_machine=%d, expected EM_AARCH64"
                    % (SHARED_OBJECT, e_machine)
                )

            # --- section table -------------------------------------------
            names = section_names(data)
            checks += 1
            if ".text" not in names:
                problems.append(
                    "%s: section table missing .text" % SHARED_OBJECT
                )
            checks += 1
            if ".codesign" not in names:
                problems.append(
                    "%s: missing .codesign section (package() signing step)"
                    % SHARED_OBJECT
                )

            # --- dynamic section: SONAME + relocatable NEEDED -------------
            soname, needed = dyn_strings(data)
            checks += 1
            if soname != SHARED_OBJECT:
                problems.append(
                    "%s: DT_SONAME=%r, expected %r"
                    % (SHARED_OBJECT, soname, SHARED_OBJECT)
                )
            checks += 1
            if not needed:
                problems.append(
                    "%s: no DT_NEEDED entries parsed" % SHARED_OBJECT
                )
            for entry in needed:
                checks += 1
                if "/" in entry or "\\" in entry:
                    problems.append(
                        "%s: DT_NEEDED %r is not a bare basename "
                        "(machine-private path baked in, E537)"
                        % (SHARED_OBJECT, entry)
                    )

    if problems:
        for problem in problems:
            print("FAIL: %s" % problem)
        return 1

    print(
        "OK: %s is an AArch64 ELF64 shared object, %d section(s), "
        ".codesign present, DT_SONAME=%s, %d DT_NEEDED basename(s)"
        % (SHARED_OBJECT, len(names), soname, len(needed))
    )
    print("OK: %d OHOS artefact checks passed" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
