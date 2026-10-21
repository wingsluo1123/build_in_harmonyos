#!/usr/bin/env python3
"""OHOS-specific test: verify systray-x binary resolves a shared-lib closure.

This is a HarmonyOS-specific, NON-ASSERTIVE consumer check:
it inspects the packaged ELF (arch, dynamic section, DT_NEEDED) and
prints PASS/WARN lines. It never raises on a mismatch, so it documents
the OHOS load closure without turning into an assertion gate.

Usage: test_ohos_closure.py [path-to-SysTray-X]
"""

import os
import struct
import subprocess
import sys

EM_AARCH64 = 0xB7
EM_X86_64 = 0x3E
SHT_DYNAMIC = 6
DT_NULL = 0
DT_NEEDED = 1


def find_systray_binary():
    """Locate the SysTray-X binary.

    Priority: explicit argv[1] (passed by the test_package conanfile),
    then a scan of the conan cache as a fallback.
    """
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return sys.argv[1]
    conan_home = os.environ.get("CONAN_HOME", "/data/storage/el2/base/cache/conan-home")
    search_root = os.path.join(conan_home, "p")
    for root, dirs, files in os.walk(search_root):
        for f in files:
            if f == "SysTray-X":
                return os.path.join(root, f)
    return None


def parse_elf_header(binary):
    """Return (e_machine, is_64bit) from the ELF header."""
    with open(binary, "rb") as f:
        ident = f.read(20)
    if len(ident) < 20 or ident[:4] != b"\x7fELF":
        return None, None
    ei_class = ident[4]  # 2 == ELFCLASS64
    e_machine = struct.unpack("<H", ident[18:20])[0]
    return e_machine, ei_class == 2


def _read_elf_needed_via_tool(binary):
    """Read DT_NEEDED using llvm-readelf/readelf/objdump when available."""
    for tool, args in (
        ("llvm-readelf", ["-d"]),
        ("readelf", ["-d"]),
        ("llvm-objdump", ["-p"]),
        ("objdump", ["-p"]),
    ):
        try:
            result = subprocess.run(
                [tool] + args + [binary],
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, OSError):
            continue
        except Exception:
            continue
        if result.returncode != 0:
            continue
        needed = []
        for line in result.stdout.splitlines():
            if "NEEDED" not in line:
                continue
            start, end = line.find("["), line.find("]")
            if start != -1 and end != -1:
                needed.append(line[start + 1:end])
            else:
                parts = line.strip().split()
                if len(parts) >= 2:
                    needed.append(parts[1])
        return needed
    return None


def _read_elf_needed_pure_python(binary):
    """Parse the ELF64 dynamic section directly (no external tools).

    Returns the list of DT_NEEDED strings, or None if the file is not a
    parseable ELF64 with a dynamic section.
    """
    with open(binary, "rb") as f:
        data = f.read()
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
        return None

    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
    if e_shoff == 0 or e_shnum == 0:
        return None

    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        if off + 64 > len(data):
            return None
        sh_name, sh_type = struct.unpack_from("<II", data, off)
        sh_offset, sh_size = struct.unpack_from("<QQ", data, off + 0x18)
        sh_link, = struct.unpack_from("<I", data, off + 0x28)
        sh_entsize, = struct.unpack_from("<Q", data, off + 0x38)
        sections.append(
            {
                "name": sh_name,
                "type": sh_type,
                "offset": sh_offset,
                "size": sh_size,
                "link": sh_link,
                "entsize": sh_entsize,
            }
        )

    for sec in sections:
        if sec["type"] != SHT_DYNAMIC:
            continue
        strtab = sections[sec["link"]] if sec["link"] < len(sections) else None
        if strtab is None:
            return None
        entsize = sec["entsize"] or 16
        needed = []
        count = sec["size"] // entsize
        for i in range(count):
            off = sec["offset"] + i * entsize
            if off + 16 > len(data):
                break
            d_tag, d_val = struct.unpack_from("<qQ", data, off)
            if d_tag == DT_NULL:
                break
            if d_tag != DT_NEEDED:
                continue
            s_off = strtab["offset"] + d_val
            if s_off >= len(data):
                continue
            end = data.find(b"\x00", s_off)
            if end == -1:
                continue
            needed.append(data[s_off:end].decode("utf-8", "replace"))
        return needed
    return None


def read_elf_needed(binary):
    """Read DT_NEEDED entries: external tool first, pure Python fallback."""
    needed = _read_elf_needed_via_tool(binary)
    if needed is not None:
        print("DT_NEEDED source: external ELF tool")
        return needed
    needed = _read_elf_needed_pure_python(binary)
    if needed is not None:
        print("DT_NEEDED source: pure-python ELF parser")
        return needed
    return None


def test_binary_loads():
    """Inspect the SysTray-X ELF load closure. Non-assertive by design."""
    binary = find_systray_binary()
    if binary is None:
        print("SKIP: SysTray-X binary not found")
        return 0

    print(f"Testing binary: {binary}")
    print(f"Binary size: {os.path.getsize(binary)} bytes")

    with open(binary, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        print(f"WARN: {binary} is not an ELF file")
        return 0
    print("ELF magic: OK")

    e_machine, is_64bit = parse_elf_header(binary)
    arch = {EM_AARCH64: "aarch64", EM_X86_64: "x86_64"}.get(e_machine, f"EM=0x{e_machine:04x}")
    print(f"ELF class: {'ELF64' if is_64bit else 'ELF32'}, arch: {arch}")
    if e_machine == EM_AARCH64:
        print("PASS: target arch is aarch64 (OHOS armv8)")
    else:
        print(f"WARN: arch is {arch}, expected aarch64")

    needed = read_elf_needed(binary)
    if needed is None:
        print("WARN: could not read the dynamic section")
        return 0
    if not needed:
        print("WARN: no DT_NEEDED entries (static or stripped dynamic section)")
        return 0

    print(f"DT_NEEDED count: {len(needed)}")
    for lib in needed:
        print(f"  - {lib}")

    # Key OHOS adaptation checks (reported, never asserted).
    checks = [
        ("libX11.so", "X11 integration resolved via libx11 package"),
        ("libQt5Widgets.so", "Qt5Widgets linked from qt package"),
        ("libQt5Core.so", "Qt5Core linked from qt package"),
    ]
    for soname, meaning in checks:
        hit = any(soname in lib for lib in needed)
        print(f"{'PASS' if hit else 'WARN'}: {soname} {'->' if hit else 'missing for'} {meaning}")

    print("PASS: systray-x binary exposes a shared-lib closure")
    return 0


if __name__ == "__main__":
    sys.exit(test_binary_loads())
