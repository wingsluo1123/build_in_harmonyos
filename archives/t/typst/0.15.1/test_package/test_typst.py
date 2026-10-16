#!/usr/bin/env python3
"""Consumer test for the packaged typst binary (test_package side).

Two layers of verification on the HarmonyOS PC host:

  1. HarmonyOS platform traits of the packaged `typst` ELF — verified by
     parsing the ELF itself (no external tooling):
       H1 e_machine == 183 (AArch64)
       H2 class == 64-bit, little-endian
       H3 PT_INTERP == /lib/ld-musl-aarch64.so.1 (OHOS musl loader, not glibc)
       H4 a `.codesign` section is present (HarmonyOS refuses to execve an
          unsigned ELF: EACCES errno 13 — this is exactly what the recipe's
          _sign_binaries() step produces)
       H5 a `.note.ohos.ident` section is present (HarmonyOS identity note)

  2. Real end-to-end usage of the packaged executable (R34 — the test must
     actually exercise the artifact, not merely print):
       * `typst --version`  → reports 0.15.1
       * `typst eval '1+2*3'` → prints 7
       * `typst compile` a real document → a valid PDF (%PDF header, >1 KiB)
       * `typst compile --format png` → a valid PNG (\\x89PNG header)
       * `typst fonts` → typst's own font discovery finds system fonts on OHOS

Exits non-zero on the first failed assertion.
"""
import os
import struct
import subprocess
import sys
import tempfile

PACKAGE_FOLDER = os.environ["PACKAGE_FOLDER"]
TYPST = os.path.join(PACKAGE_FOLDER, "bin", "typst")

PASSED = 0
FAILED = 0


def check(name, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  [PASS] {name}{(' — ' + detail) if detail else ''}")
    else:
        FAILED += 1
        print(f"  [FAIL] {name}{(' — ' + detail) if detail else ''}")


def parse_elf(path):
    d = open(path, "rb").read()
    assert d[:4] == b"\x7fELF", "not an ELF file"
    is64 = d[4] == 2
    little = d[5] == 1
    e_machine = struct.unpack_from("<H", d, 18)[0]
    if is64:
        e_phoff = struct.unpack_from("<Q", d, 32)[0]
        e_shoff = struct.unpack_from("<Q", d, 40)[0]
        e_shentsize = struct.unpack_from("<H", d, 58)[0]
        e_shnum = struct.unpack_from("<H", d, 60)[0]
        e_shstrndx = struct.unpack_from("<H", d, 62)[0]
    else:
        e_phoff = struct.unpack_from("<I", d, 28)[0]
        e_shoff = struct.unpack_from("<I", d, 32)[0]
        e_shentsize = struct.unpack_from("<H", d, 46)[0]
        e_shnum = struct.unpack_from("<H", d, 48)[0]
        e_shstrndx = struct.unpack_from("<H", d, 50)[0]
    e_phentsize = struct.unpack_from("<H", d, 54 if is64 else 42)[0]
    e_phnum = struct.unpack_from("<H", d, 56 if is64 else 44)[0]
    interp = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if struct.unpack_from("<I", d, off)[0] == 3:  # PT_INTERP
            if is64:
                p_off = struct.unpack_from("<Q", d, off + 8)[0]
                p_fsz = struct.unpack_from("<Q", d, off + 32)[0]
            else:
                p_off = struct.unpack_from("<I", d, off + 4)[0]
                p_fsz = struct.unpack_from("<I", d, off + 16)[0]
            interp = d[p_off:p_off + p_fsz].split(b"\0")[0].decode("ascii", "replace")
    names = []
    if e_shnum and e_shoff:
        strtab_off = struct.unpack_from(
            "<Q" if is64 else "<I", d, e_shoff + e_shstrndx * e_shentsize + (24 if is64 else 16))[0]
        for i in range(e_shnum):
            s_off = e_shoff + i * e_shentsize
            name_off = struct.unpack_from("<I", d, s_off)[0]
            end = d.index(b"\0", strtab_off + name_off)
            names.append(d[strtab_off + name_off:end].decode("ascii", "replace"))
    return is64, little, e_machine, interp, names


def run(args, **kw):
    return subprocess.run([TYPST] + args, capture_output=True, text=True, **kw)


def main():
    print(f"typst consumer test — package_folder={PACKAGE_FOLDER}")
    print(f"typst binary: {TYPST}")
    check("binary exists & is non-empty",
          os.path.isfile(TYPST) and os.path.getsize(TYPST) > 1_000_000,
          f"{os.path.getsize(TYPST) if os.path.isfile(TYPST) else 0} bytes")

    # ── HarmonyOS platform traits (static ELF analysis) ────────────────
    is64, little, e_machine, interp, sections = parse_elf(TYPST)
    check("H1 ELF e_machine == 183 (AArch64)", e_machine == 183, hex(e_machine))
    check("H2 ELF is 64-bit little-endian", is64 and little)
    check("H3 PT_INTERP == /lib/ld-musl-aarch64.so.1 (OHOS musl loader)",
          interp == "/lib/ld-musl-aarch64.so.1", str(interp))
    check("H4 .codesign section present (OHOS exec requirement)",
          ".codesign" in sections)
    check("H5 .note.ohos.ident section present (OHOS identity)",
          ".note.ohos.ident" in sections)

    # ── Real usage of the executable (R34) ─────────────────────────────
    r = run(["--version"])
    check("--version succeeds", r.returncode == 0, r.stdout.strip())
    check("--version reports 0.15.1", "0.15.1" in r.stdout)

    r = run(["eval", "1+2*3"])
    check("eval '1+2*3' == 7", r.returncode == 0 and r.stdout.strip() == "7",
          r.stdout.strip())

    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "hello.typ")
        with open(src, "w") as f:
            f.write("= Hello HarmonyOS\n"
                    "Typst running natively on aarch64-unknown-linux-ohos.\n"
                    "$ sum_(i=1)^n i = (n(n+1))/2 $\n")
        pdf = os.path.join(td, "hello.pdf")
        r = run(["compile", src, pdf])
        ok_pdf = (r.returncode == 0 and os.path.isfile(pdf)
                  and os.path.getsize(pdf) > 1024
                  and open(pdf, "rb").read(4) == b"%PDF")
        check("compile document -> valid PDF", ok_pdf,
              f"{os.path.getsize(pdf) if os.path.isfile(pdf) else 0} bytes")
        png = os.path.join(td, "hello.png")
        r = run(["compile", "--format", "png", src, png])
        ok_png = (r.returncode == 0 and os.path.isfile(png)
                  and open(png, "rb").read(4) == b"\x89PNG")
        check("compile --format png -> valid PNG", ok_png)

    r = run(["fonts"])
    listed = [ln for ln in r.stdout.splitlines() if ln.strip()]
    check("H6 `typst fonts` discovers system fonts on OHOS",
          r.returncode == 0 and len(listed) >= 1,
          f"{len(listed)} font families")

    print(f"\nRESULT: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
