#!/usr/bin/env python3
"""Print SONAME / NEEDED / RPATH / RUNPATH of an ELF64 shared object or executable.

Used from the qtwebchannel test_package to prove *why* the loader refuses a library
(absolute build-tree paths in DT_NEEDED are the classic failure on OHOS).
Pure stdlib, works with python3 in the CI sandbox.
"""
import struct
import sys


def dyn_entries(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        return None, "not an ELF file"
    is64 = data[4] == 2
    endian = "<" if data[5] == 1 else ">"
    if not is64:
        return None, "only ELF64 supported"
    e_phoff = struct.unpack_from(endian + "Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from(endian + "H", data, 0x36)[0]
    e_phnum = struct.unpack_from(endian + "H", data, 0x38)[0]
    dyn_off = dyn_size = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from(endian + "I", data, off)[0]
        if p_type == 2:  # PT_DYNAMIC
            dyn_off = struct.unpack_from(endian + "Q", data, off + 8)[0]
            dyn_size = struct.unpack_from(endian + "Q", data, off + 32)[0]
    if dyn_off is None:
        return None, "no PT_DYNAMIC"
    strtab = None
    raw = []
    for off in range(dyn_off, dyn_off + dyn_size, 16):
        tag, val = struct.unpack_from(endian + "qQ", data, off)
        raw.append((tag, val))
        if tag == 5:  # DT_STRTAB
            strtab = val
        if tag == 0:  # DT_NULL
            break
    if strtab is None:
        return None, "no DT_STRTAB"

    def s(vi):
        e = data.index(b"\x00", vi)
        return data[vi:e].decode("utf-8", "replace")

    # vaddr -> file offset via program headers
    def v2o(va):
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type = struct.unpack_from(endian + "I", data, off)[0]
            if p_type != 1:  # PT_LOAD
                continue
            p_off = struct.unpack_from(endian + "Q", data, off + 8)[0]
            p_va = struct.unpack_from(endian + "Q", data, off + 16)[0]
            p_fsz = struct.unpack_from(endian + "Q", data, off + 32)[0]
            if p_va <= va < p_va + p_fsz:
                return p_off + (va - p_va)
        return None

    out = {"SONAME": None, "NEEDED": [], "RPATH": None, "RUNPATH": None}
    for tag, val in raw:
        if tag in (14, 1, 15, 29):
            o = v2o(strtab + val) if False else strtab + val
            # strtab value is already a file offset in practice for these binaries
            try:
                txt = s(o)
            except ValueError:
                try:
                    txt = s(v2o(strtab + val))
                except Exception:
                    txt = "<unreadable>"
            if tag == 14:
                out["SONAME"] = txt
            elif tag == 1:
                out["NEEDED"].append(txt)
            elif tag == 15:
                out["RPATH"] = txt
            else:
                out["RUNPATH"] = txt
    return out, None


if __name__ == "__main__":
    for p in sys.argv[1:]:
        info, err = dyn_entries(p)
        print("=== " + p)
        if err:
            print("    ! " + err)
            continue
        print("    SONAME  =", info["SONAME"])
        print("    RPATH   =", info["RPATH"], "| RUNPATH =", info["RUNPATH"])
        for n in info["NEEDED"]:
            flag = "  <-- ABSOLUTE PATH!" if n.startswith("/") else ""
            print("    NEEDED  =", n + flag)
