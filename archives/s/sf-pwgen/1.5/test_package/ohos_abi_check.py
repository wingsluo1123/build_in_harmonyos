#!/usr/bin/env python3
"""HarmonyOS artifact/ABI checks for sf-pwgen 1.5 (pure Python, no external tools).

Checks (any host can run; they inspect the artifact, not execute it):
  A1  ELF64 + e_machine == EM_AARCH64      HarmonyOS PC arm64 target
  A2  .interp == /lib/ld-musl-aarch64.so.1 OHOS musl loader (glibc would be
                                           /lib/ld-linux-aarch64.so.1)
  A3  DT_NEEDED contains libc.so and no libcrypto/libssl
                                           zero-dependency proof for the
                                           portable backend (no macOS
                                           framework residue is expressible
                                           in ELF, no third-party .so)

Exit code 0 = all executed checks passed, 1 = at least one failure.
"""
import argparse
import json
import struct
import sys

ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
DT_NEEDED = 1
DT_STRTAB = 5
DT_NULL = 0

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"


class ElfError(Exception):
    pass


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _sections(data):
    """Return (e_machine, [(name, sh_type, sh_offset, sh_size, sh_link)])."""
    if data[:4] != b"\x7fELF":
        raise ElfError("not an ELF file (bad magic %r)" % data[:4])
    if data[4] != ELFCLASS64:
        raise ElfError("not ELF64 (EI_CLASS=%d)" % data[4])
    if data[5] != ELFDATA2LSB:
        raise ElfError("not little-endian (EI_DATA=%d)" % data[5])
    (e_machine,) = struct.unpack_from("<H", data, 18)
    (e_shoff,) = struct.unpack_from("<Q", data, 40)
    (e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHH", data, 58)
    if e_shoff == 0 or e_shnum == 0:
        raise ElfError("no section headers")
    hdrs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        name, sh_type, _flags, _addr, sh_offset, sh_size, sh_link, _info, \
            _align, _entsize = struct.unpack_from("<IIQQQQIIQQ", data, off)
        hdrs.append((name, sh_type, sh_offset, sh_size, sh_link))
    shstr_off, shstr_size = hdrs[e_shstrndx][2], hdrs[e_shstrndx][3]
    shstr = data[shstr_off:shstr_off + shstr_size]
    out = []
    for name_idx, sh_type, sh_offset, sh_size, sh_link in hdrs:
        end = shstr.find(b"\x00", name_idx)
        out.append((shstr[name_idx:end].decode("utf-8", "replace"),
                    sh_type, sh_offset, sh_size, sh_link))
    return e_machine, out


def _section(data, sections, name):
    for sec in sections:
        if sec[0] == name:
            return sec
    return None


def _strtab(data, sections, idx):
    sec = sections[idx]
    return data[sec[2]:sec[2] + sec[3]]


def _cstr(blob, offset):
    end = blob.find(b"\x00", offset)
    return blob[offset:end if end >= 0 else len(blob)].decode("utf-8", "replace")


def check_binary(path):
    """A1-A3 on a linked executable. Returns [(name, ok, detail)]."""
    results = []
    data = _read(path)
    e_machine, sections = _sections(data)

    ok = e_machine == EM_AARCH64
    results.append((
        "A1_elf64_aarch64", ok,
        "ELF64 little-endian, e_machine=%d (%s)" % (
            e_machine, "EM_AARCH64" if ok else "not EM_AARCH64(%d)" % EM_AARCH64)))

    interp = _section(data, sections, ".interp")
    if interp is None:
        results.append(("A2_ohos_musl_interp", False, ".interp section missing"))
    else:
        value = _cstr(data[interp[2]:interp[2] + interp[3]], 0)
        results.append((
            "A2_ohos_musl_interp", value == OHOS_INTERP,
            "PT_INTERP=%s (expected %s)" % (value, OHOS_INTERP)))

    dyn = _section(data, sections, ".dynamic")
    if dyn is None:
        results.append(("A3_zero_deps", False, ".dynamic section missing"))
    else:
        strtab = _strtab(data, sections, dyn[4])
        needed, off, blob = [], dyn[2], data
        while off + 16 <= dyn[2] + dyn[3]:
            tag, val = struct.unpack_from("<qQ", blob, off)
            off += 16
            if tag == DT_NULL:
                break
            if tag == DT_NEEDED:
                needed.append(_cstr(strtab, val))
        bad = [n for n in needed
               if n.startswith("libcrypto") or n.startswith("libssl")]
        ok = ("libc.so" in needed) and not bad
        results.append((
            "A3_zero_deps", ok,
            "DT_NEEDED=%s (crypto shared deps: %s)" % (
                needed or "[]", bad or "none")))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", required=True,
                    help="linked sf-pwgen executable to inspect")
    args = ap.parse_args(argv)

    results = []
    try:
        results.extend(check_binary(args.binary))
    except (ElfError, OSError, struct.error) as exc:
        print("OHOS_ABI_CHECK_FAILED: %s" % exc)
        return 1

    passed = 0
    for name, ok, detail in results:
        print("[%s] %s: %s" % ("PASS" if ok else "FAIL", name, detail))
        passed += 1 if ok else 0
    summary = {
        "binary": args.binary,
        "discovered": len(results),
        "passed": passed,
        "failed": len(results) - passed,
    }
    print("OHOS_ABI_CHECK=" + json.dumps(summary))
    return 0 if passed == len(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
