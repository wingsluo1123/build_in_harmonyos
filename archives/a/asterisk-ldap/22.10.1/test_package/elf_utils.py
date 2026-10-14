#!/usr/bin/env python3
"""Minimal ELF64 dynamic-information parser (no external binutils needed).

Used by the asterisk-ldap test_package to inspect the packaged module with
nothing but the Python standard library: ELF header, program headers,
PT_DYNAMIC tags (DT_NEEDED / DT_RPATH / DT_RUNPATH / DT_INIT_ARRAY),
and the undefined entries of .dynsym.
"""
import struct

ELF_MAGIC = b"\x7fELF"

EM_AARCH64 = 183
ET_DYN = 3

PT_LOAD = 1
PT_DYNAMIC = 2

DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_SYMTAB = 6
DT_STRSZ = 10
DT_SYMENT = 11
DT_RPATH = 15
DT_INIT_ARRAY = 25
DT_INIT_ARRAYSZ = 27
DT_RUNPATH = 29

SHN_UNDEF = 0


class ElfError(Exception):
    pass


def _load_segments(blob, e_phoff, e_phentsize, e_phnum):
    segs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        (p_type, _flags, p_offset, p_vaddr, _p_paddr,
         p_filesz, _p_memsz, _p_align) = struct.unpack_from("<IIQQQQQQ", blob, off)
        segs.append({"type": p_type, "offset": p_offset, "vaddr": p_vaddr,
                     "filesz": p_filesz})
    return segs


def _vaddr_to_offset(segs, vaddr):
    for seg in segs:
        if seg["type"] == PT_LOAD and seg["vaddr"] <= vaddr < seg["vaddr"] + seg["filesz"]:
            return seg["offset"] + (vaddr - seg["vaddr"])
    return None


def parse(path):
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:4] != ELF_MAGIC:
        raise ElfError("not an ELF file")
    if blob[4] != 2 or blob[5] != 1:
        raise ElfError("only ELF64 little-endian is supported")
    (e_type, e_machine) = struct.unpack_from("<HH", blob, 16)
    (e_phoff,) = struct.unpack_from("<Q", blob, 32)
    (e_phentsize, e_phnum) = struct.unpack_from("<HH", blob, 54)

    segs = _load_segments(blob, e_phoff, e_phentsize, e_phnum)
    dynamic = None
    for seg in segs:
        if seg["type"] == PT_DYNAMIC:
            dynamic = seg
            break
    if dynamic is None:
        raise ElfError("no PT_DYNAMIC segment")

    tags = {}
    pos = dynamic["offset"]
    while True:
        (d_tag, d_val) = struct.unpack_from("<qQ", blob, pos)
        pos += 16
        if d_tag == DT_NULL:
            break
        tags.setdefault(d_tag, d_val)

    def _strtab():
        off = _vaddr_to_offset(segs, tags.get(DT_STRTAB))
        if off is None:
            raise ElfError("cannot map DT_STRTAB")
        size = tags.get(DT_STRSZ, 0)
        return blob[off:off + size], off

    strtab, strtab_off = _strtab()

    def _str(offset):
        end = strtab.find(b"\0", offset)
        return strtab[offset:end].decode("utf-8", "replace")

    needed = []
    # DT_NEEDED repeats; re-walk the dynamic array to collect them all.
    pos = dynamic["offset"]
    while True:
        (d_tag, d_val) = struct.unpack_from("<qQ", blob, pos)
        pos += 16
        if d_tag == DT_NULL:
            break
        if d_tag == DT_NEEDED:
            needed.append(_str(d_val))

    symtab_off = _vaddr_to_offset(segs, tags.get(DT_SYMTAB))
    if symtab_off is None:
        raise ElfError("cannot map DT_SYMTAB")
    syment = tags.get(DT_SYMENT, 24)
    # .dynsym is followed by .dynstr in the file for our layout; bound the scan
    # by the distance to the string table when it is after the symbol table.
    if strtab_off > symtab_off:
        nsyms = (strtab_off - symtab_off) // syment
    else:
        raise ElfError("unexpected .dynsym/.dynstr ordering")

    undefined = []
    defined = []
    for i in range(nsyms):
        off = symtab_off + i * syment
        (st_name, _st_info, _st_other, st_shndx) = struct.unpack_from("<IBBH", blob, off)
        if st_name == 0:
            continue
        name = _str(st_name)
        if st_shndx == SHN_UNDEF:
            undefined.append(name)
        else:
            defined.append(name)

    return {
        "e_type": e_type,
        "e_machine": e_machine,
        "needed": needed,
        "rpath": _str(tags[DT_RPATH]) if DT_RPATH in tags else None,
        "runpath": _str(tags[DT_RUNPATH]) if DT_RUNPATH in tags else None,
        "init_array": tags.get(DT_INIT_ARRAY),
        "init_array_sz": tags.get(DT_INIT_ARRAYSZ, 0),
        "undefined": undefined,
        "defined": defined,
        "blob": blob,
    }
