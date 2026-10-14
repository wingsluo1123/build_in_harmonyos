#!/usr/bin/env python3
"""Consumer suite for the packaged xsetroot program.

Assertions are made against the artifact shipped inside the Conan package
folder — the compiled bin/xsetroot — never against the test's own bookkeeping.
Named use cases (HC-N) make a partial failure visible.

  HC-1  packaged binary contract: it is a real AArch64 ELF64 executable, and it
        reproduces upstream's own usage banner + exit status for a bad option.
  HC-2  upstream version contract: `xsetroot -version` prints PACKAGE_STRING and
        exits 0 without contacting an X server (the option is handled before any
        XOpenDisplay), so this asserts the program actually runs here.
  HC-3  option surface: the shipped usage banner advertises the upstream option
        set (-bitmap / -cursor / -mod / -solid / -gray / -name …), i.e. the full
        feature set is compiled in rather than a stub.
  HC-4  HarmonyOS packaging invariant: the shipped ELF carries no absolute-path
        DT_NEEDED leakage (relocatable), so it stays consumable on another host.

The harness parses ELF itself (see _Elf) instead of calling binutils: the CI
worker image does not reliably provide nm/readelf/strings, and depending on them
made a sibling package's suite fail with FileNotFoundError on CI.

Usage: test_xsetroot.py <exe> <workdir>
"""
import os
import struct
import subprocess
import sys

CHECKS = {"ok": 0, "fail": 0}
CASES = []


def case_begin(cid, title):
    print(f"case {cid} RUN  {title}")


def case_end(cid, ok):
    CASES.append((cid, "PASS" if ok else "FAIL"))
    print(f"case {cid} {'PASS' if ok else 'FAIL'}")


def check(cond, name, detail=""):
    if cond:
        CHECKS["ok"] += 1
        print(f"ok   - {name}")
    else:
        CHECKS["fail"] += 1
        print(f"FAIL - {name}: {detail}")


def run(cmd, timeout=60):
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace", timeout=timeout)


class _Elf:
    """Minimal, dependency-free ELF64/LE reader (header + dynamic table)."""

    DT_NULL, DT_NEEDED, DT_STRTAB, DT_STRSZ = 0, 1, 5, 10
    PT_LOAD = 1

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh:
            self.data = fh.read()
        d = self.data
        if len(d) < 64 or d[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        self.ei_class, self.ei_data = d[4], d[5]
        if self.ei_class != 2 or self.ei_data != 1:
            raise ValueError("only ELF64 little-endian is supported")
        self.e_type, self.e_machine = struct.unpack_from("<HH", d, 16)
        (self.e_phoff,) = struct.unpack_from("<Q", d, 32)
        (self.e_shoff,) = struct.unpack_from("<Q", d, 40)
        self.e_phentsize, self.e_phnum = struct.unpack_from("<HH", d, 54)
        self.e_shentsize, self.e_shnum = struct.unpack_from("<HH", d, 58)
        self.e_shstrndx = struct.unpack_from("<H", d, 62)[0]

    @property
    def program_headers(self):
        out = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            p_type, _flags = struct.unpack_from("<II", self.data, off)
            p_offset, p_vaddr = struct.unpack_from("<QQ", self.data, off + 8)
            p_filesz = struct.unpack_from("<Q", self.data, off + 32)[0]
            out.append({"type": p_type, "offset": p_offset,
                        "vaddr": p_vaddr, "filesz": p_filesz})
        return out

    @property
    def sections(self):
        out = []
        shstr_off = self.e_shoff + self.e_shstrndx * self.e_shentsize
        shstr_sh_offset = struct.unpack_from("<Q", self.data, shstr_off + 24)[0]
        shstr_size = struct.unpack_from("<Q", self.data, shstr_off + 32)[0]
        shstr = self.data[shstr_sh_offset:shstr_sh_offset + shstr_size]
        for i in range(self.e_shnum):
            off = self.e_shoff + i * self.e_shentsize
            sh_name, _sh_type = struct.unpack_from("<II", self.data, off)
            sh_offset, sh_size = struct.unpack_from("<QQ", self.data, off + 24)
            end = shstr.find(b"\x00", sh_name)
            name = shstr[sh_name:end].decode("utf-8", "replace") if sh_name else ""
            out.append({"name": name, "offset": sh_offset, "size": sh_size})
        return out

    def section(self, name):
        for s in self.sections:
            if s["name"] == name:
                return s
        return None

    @property
    def dynamic(self):
        dyn = self.section(".dynamic")
        if dyn is None:
            for ph in self.program_headers:
                if ph["type"] == 2:  # PT_DYNAMIC
                    dyn = {"offset": ph["offset"], "size": ph["filesz"]}
                    break
        if not dyn or not dyn.get("size"):
            return []
        return [struct.unpack_from("<QQ", self.data, dyn["offset"] + i * 16)
                for i in range(dyn["size"] // 16)]

    def _dynstr(self):
        """Return the raw .dynstr bytes, sized by DT_STRSZ.

        Sizing matters: offset 0 of a dynamic string table is the empty string,
        so slicing "up to the first NUL" would return an empty buffer and make
        every DT_NEEDED lookup yield "" — silently neutering the HC-4 assertion.
        """
        strtab_va = strsz = None
        for tag, val in self.dynamic:
            if tag == self.DT_STRTAB:
                strtab_va = val
            elif tag == self.DT_STRSZ:
                strsz = val
        if strtab_va is None or not strsz:
            return b""
        for ph in self.program_headers:
            if ph["type"] == self.PT_LOAD and \
                    ph["vaddr"] <= strtab_va < ph["vaddr"] + ph["filesz"]:
                start = ph["offset"] + (strtab_va - ph["vaddr"])
                return self.data[start:start + strsz]
        return b""

    @property
    def needed(self):
        strtab = self._dynstr()
        if not strtab:
            # A missing string table alongside DT_NEEDED entries is a parsing
            # failure, not "no dependencies" — surface it instead of reporting a
            # vacuous empty list that would let HC-4 pass unconditionally.
            if any(tag == self.DT_NEEDED for tag, _ in self.dynamic):
                raise ValueError("DT_NEEDED present but the dynamic string "
                                 "table could not be read")
            return []
        out = []
        for tag, val in self.dynamic:
            if tag == self.DT_NEEDED:
                end = strtab.find(b"\x00", val)
                out.append(strtab[val:end if end != -1 else len(strtab)]
                           .decode("utf-8", "replace"))
        return out


# ── HC-1: packaged binary + upstream CLI contract ────────────────────────────
def hc1_binary_contract(exe):
    case_begin("HC-1", "packaged xsetroot binary + upstream usage contract")
    ok = True
    before = CHECKS["fail"]

    check(os.path.isfile(exe), "HC-1.1 packaged bin/xsetroot exists", exe)
    if not os.path.isfile(exe):
        case_end("HC-1", False)
        return
    check(os.access(exe, os.X_OK), "HC-1.2 packaged xsetroot is executable")

    try:
        elf = _Elf(exe)
        check(True, "HC-1.3 packaged xsetroot is an ELF file")
        check(elf.ei_class == 2, "HC-1.4 packaged xsetroot is ELF64",
              f"EI_CLASS={elf.ei_class}")
        check(elf.e_machine == 0xB7, "HC-1.5 packaged xsetroot targets AArch64",
              f"e_machine=0x{elf.e_machine:x}")
    except ValueError as exc:
        check(False, "HC-1.3 packaged xsetroot is an ELF file", str(exc))
        ok = False

    # An unknown option falls through to usage() and exits 1 (xsetroot.c:96).
    bad = run([exe, "-not-an-option"])
    err = bad.stderr or ""
    check("Usage:" in err, "HC-1.6 bad option prints upstream usage banner",
          err[:200])
    check(bad.returncode == 1, "HC-1.7 bad option exits with status 1",
          f"rc={bad.returncode}")

    if CHECKS["fail"] != before:
        ok = False
    case_end("HC-1", ok)


# ── HC-2: the version contract really executes the program ───────────────────
def hc2_version_contract(exe):
    case_begin("HC-2", "xsetroot -version executes and reports PACKAGE_STRING")
    ok = True
    before = CHECKS["fail"]

    # xsetroot.c handles -version before any XOpenDisplay call, printing
    # PACKAGE_STRING ("xsetroot 1.1.3") and exiting 0 — so this works headless.
    proc = run([exe, "-version"])
    out = (proc.stdout or "").strip()
    check(proc.returncode == 0, "HC-2.1 -version exits with status 0",
          f"rc={proc.returncode} stderr={(proc.stderr or '')[:200]}")
    check("xsetroot" in out, "HC-2.2 -version reports the program name", out[:200])
    check("1.1.3" in out, "HC-2.3 -version reports upstream version 1.1.3", out[:200])

    if CHECKS["fail"] != before:
        ok = False
    case_end("HC-2", ok)


# ── HC-3: the full upstream option surface is compiled in ────────────────────
def hc3_option_surface(exe):
    case_begin("HC-3", "shipped usage banner advertises the upstream options")
    ok = True
    before = CHECKS["fail"]

    err = run([exe, "-help"]).stderr or ""
    for option in ("-bitmap", "-cursor", "-cursor_name", "-xcf", "-mod",
                   "-gray", "-solid", "-name", "-display", "-def"):
        check(option in err,
              f"HC-3.x usage advertises {option}",
              f"missing from banner: {err[:300]}")

    if CHECKS["fail"] != before:
        ok = False
    case_end("HC-3", ok)


# ── HC-4: HarmonyOS packaging invariant ──────────────────────────────────────
def hc4_packaging_invariant(exe):
    case_begin("HC-4", "HarmonyOS packaging invariant of the shipped ELF")
    ok = True
    before = CHECKS["fail"]

    try:
        needed = _Elf(exe).needed
    except ValueError as exc:
        check(False, "HC-4.1 packaged ELF can be parsed", str(exc))
        case_end("HC-4", False)
        return
    check(True, "HC-4.1 packaged ELF can be parsed")
    check(bool(needed), "HC-4.2 shipped ELF declares DT_NEEDED entries", "none")
    # A package must never bake a machine-private absolute path into DT_NEEDED,
    # otherwise it is not consumable on another machine.
    absolute = [n for n in needed if "/" in n]
    check(not absolute,
          "HC-4.3 no absolute-path leakage in DT_NEEDED (relocatable)",
          f"leaked={absolute}")

    if CHECKS["fail"] != before:
        ok = False
    case_end("HC-4", ok)


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <exe> <workdir>", file=sys.stderr)
        return 2
    exe, _workdir = sys.argv[1], sys.argv[2]

    print("== xsetroot consumer suite ==")
    print(f"   exe = {exe}")

    hc1_binary_contract(exe)
    hc2_version_contract(exe)
    hc3_option_surface(exe)
    hc4_packaging_invariant(exe)

    failed = sum(1 for _c, v in CASES if v == "FAIL")
    print(f"== {len(CASES)} cases, {failed} failed ==")
    print(f"== {CHECKS['ok'] + CHECKS['fail']} checks, {CHECKS['fail']} failures ==")
    if failed == 0 and CHECKS["fail"] == 0:
        print("RESULT: PASSED")
        return 0
    print("RESULT: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
