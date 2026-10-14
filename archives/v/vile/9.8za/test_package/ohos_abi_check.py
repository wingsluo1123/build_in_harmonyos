#!/usr/bin/env python3
"""HarmonyOS ABI checks for the packaged vile executable."""

import argparse
import json
import struct
import sys

ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
SHT_DYNAMIC = 6
DT_NEEDED = 1
DT_NULL = 0
OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"


class ElfError(Exception):
    pass


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


def _sections(data):
    if data[:4] != b"\x7fELF":
        raise ElfError("not an ELF file")
    if data[4] != ELFCLASS64:
        raise ElfError("not ELF64")
    if data[5] != ELFDATA2LSB:
        raise ElfError("not little-endian")
    (e_machine,) = struct.unpack_from("<H", data, 18)
    (e_shoff,) = struct.unpack_from("<Q", data, 40)
    (e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHH", data, 58)
    if e_shoff == 0 or e_shnum == 0:
        raise ElfError("no section headers")

    headers = []
    for index in range(e_shnum):
        offset = e_shoff + index * e_shentsize
        fields = struct.unpack_from("<IIQQQQIIQQ", data, offset)
        headers.append(fields)

    shstr_header = headers[e_shstrndx]
    shstr = data[shstr_header[4]:shstr_header[4] + shstr_header[5]]
    sections = []
    for header in headers:
        name_offset = header[0]
        end = shstr.find(b"\x00", name_offset)
        name = shstr[name_offset:end].decode("utf-8", "replace")
        sections.append((name, header[1], header[4], header[5], header[6]))
    return e_machine, sections


def _section(sections, name):
    for section in sections:
        if section[0] == name:
            return section
    return None


def _cstring(blob, offset):
    end = blob.find(b"\x00", offset)
    return blob[offset:end].decode("utf-8", "replace")


def check_binary(path):
    results = []
    data = _read(path)
    e_machine, sections = _sections(data)

    results.append((
        "A1_elf64_aarch64",
        e_machine == EM_AARCH64,
        f"e_machine={e_machine} (expected {EM_AARCH64})",
    ))

    interp = _section(sections, ".interp")
    if interp is None:
        results.append(("A2_ohos_musl_interp", False, ".interp section missing"))
    else:
        value = _cstring(data[interp[2]:interp[2] + interp[3]], 0)
        results.append((
            "A2_ohos_musl_interp",
            value == OHOS_INTERP,
            f"PT_INTERP={value} (expected {OHOS_INTERP})",
        ))

    dynamic = _section(sections, ".dynamic")
    if dynamic is None:
        results.append(("A3_static_ncurses", False, ".dynamic section missing"))
    else:
        strtab = _section(sections, ".dynstr")
        if strtab is None:
            results.append(("A3_static_ncurses", False, ".dynstr section missing"))
        else:
            strings = data[strtab[2]:strtab[2] + strtab[3]]
            needed = []
            offset = dynamic[2]
            while offset + 16 <= dynamic[2] + dynamic[3]:
                tag, value = struct.unpack_from("<qQ", data, offset)
                offset += 16
                if tag == DT_NULL:
                    break
                if tag == DT_NEEDED:
                    needed.append(_cstring(strings, value))
            shared_ncurses = [
                name for name in needed if name.startswith("libncurses")
            ]
            results.append((
                "A3_static_ncurses",
                not shared_ncurses,
                f"DT_NEEDED={needed} (ncurses shared deps: {shared_ncurses or 'none'})",
            ))

    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    args = parser.parse_args(argv)

    try:
        results = check_binary(args.binary)
    except (ElfError, OSError, struct.error) as exc:
        print(f"OHOS_ABI_CHECK_FAILED: {exc}")
        return 1

    passed = sum(1 for _name, ok, _detail in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print("OHOS_ABI_CHECK=" + json.dumps({
        "binary": args.binary,
        "discovered": len(results),
        "passed": passed,
        "failed": len(results) - passed,
    }))
    return 0 if results and passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
