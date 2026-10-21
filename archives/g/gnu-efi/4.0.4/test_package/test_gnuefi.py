#!/usr/bin/env python3
"""Consumer test for the gnu-efi Conan package.

Builds a real UEFI application against the packaged toolkit (crt0 stub +
elf_aarch64_efi.lds + libefi.a + libgnuefi.a), converts the ELF image to a
PE32+ EFI binary with objcopy, and checks the resulting image is a valid
EFI application for aarch64.

Every check goes through Checks.check() so the run ends with a printed
`assertions N/M` line — the assertion count in MANIFEST.yml is thus a
machine-visible reading rather than a self-declaration.
"""

import os
import shutil
import struct
import subprocess
import sys

EFI_ARCH = "aarch64"
PE_MACHINE_AARCH64 = 0xAA64
EFI_APPLICATION_SUBSYSTEM = 10

SOURCE = r"""
#include <efi.h>
#include <efilib.h>

EFI_STATUS efi_main(EFI_HANDLE image, EFI_SYSTEM_TABLE *systab)
{
	InitializeLib(image, systab);
	Print(u"gnu-efi consumer smoke test\n");
	return EFI_SUCCESS;
}
"""


class Checks:
    """Counted assertions: 16 in total (13 value + 3 post-run arrival)."""

    def __init__(self):
        self.passed = 0
        self.total = 0

    def check(self, condition, message):
        self.total += 1
        if not condition:
            raise AssertionError("assertion %d/%d failed: %s"
                                 % (self.total, self.total, message))
        self.passed += 1

    def report(self):
        print("assertions %d/%d" % (self.passed, self.total))


def find(*names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError("none of these tools found on PATH: %s" % (names,))


def run(cmd, **kwargs):
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main():
    checks = Checks()
    pkg = os.path.abspath(sys.argv[1])
    inc = os.path.join(pkg, "include", "efi")
    libdir = os.path.join(pkg, "lib")
    work = os.path.abspath("gnuefi-consumer")

    checks.check(os.path.isfile(os.path.join(inc, "efi.h")),
                 "packaged EFI headers missing")
    checks.check(os.path.isfile(os.path.join(inc, "efilib.h")),
                 "packaged efilib.h missing")
    checks.check(os.path.isfile(os.path.join(libdir, "libefi.a")), "libefi.a missing")
    checks.check(os.path.isfile(os.path.join(libdir, "libgnuefi.a")),
                 "libgnuefi.a missing")
    crt0 = os.path.join(libdir, "crt0-efi-%s.o" % EFI_ARCH)
    checks.check(os.path.isfile(crt0), "crt0-efi-%s.o missing" % EFI_ARCH)
    ldscript = os.path.join(libdir, "elf_%s_efi.lds" % EFI_ARCH)
    checks.check(os.path.isfile(ldscript), "elf_%s_efi.lds missing" % EFI_ARCH)
    pc = os.path.join(libdir, "pkgconfig", "gnu-efi.pc")
    checks.check(os.path.isfile(pc), "gnu-efi.pc missing")
    with open(pc, encoding="utf-8") as handle:
        pc_text = handle.read()
    checks.check("${pcfiledir}" in pc_text,
                 "gnu-efi.pc is not relocatable: %r" % pc_text)

    os.makedirs(work, exist_ok=True)
    cc = find("clang", "gcc")
    ld = find("ld.lld", "ld")
    objcopy = find("objcopy")
    src = os.path.join(work, "hello.c")
    obj = os.path.join(work, "hello.o")
    so = os.path.join(work, "hello.so")
    efi = os.path.join(work, "hello.efi")
    with open(src, "w", encoding="utf-8") as handle:
        handle.write(SOURCE)

    run([cc, "-c", src, "-o", obj,
         "-I" + inc,
         "-I" + os.path.join(inc, EFI_ARCH),
         "-I" + os.path.join(inc, "protocol"),
         "-ffreestanding", "-fno-stack-protector", "-fPIC", "-fno-jump-tables",
         "-std=c11", "-O2", "-g", "-Wall", "-Wextra", "-Werror",
         "-DCONFIG_%s" % EFI_ARCH])
    # arrival check: the compile step above runs with check=True
    checks.check(os.path.isfile(obj), "compiling against the packaged headers failed")

    link_cmd = [ld, "-z", "common-page-size=4096", "-z", "max-page-size=4096",
                "-nostdlib", "--warn-common", "--no-undefined", "--fatal-warnings",
                "--build-id=sha1", "-z", "norelro", "-z", "nocombreloc",
                "-L" + libdir, crt0, "-pie", "-Bsymbolic", "--no-dynamic-linker",
                obj, "-o", so, "-T", ldscript, "-lefi", "-lgnuefi"]
    builtins = subprocess.run([cc, "-print-libgcc-file-name"],
                              capture_output=True, text=True, check=False).stdout.strip()
    if builtins and os.path.isfile(builtins):
        link_cmd.append(builtins)
    run(link_cmd)
    # arrival check: the link step above runs with check=True
    checks.check(os.path.isfile(so), "linking an EFI image failed")
    with open(so, "rb") as handle:
        checks.check(handle.read(4) == b"\x7fELF",
                     "linked artifact is not an ELF image")

    run([objcopy,
         "-j", ".text", "-j", ".sdata", "-j", ".data", "-j", ".dynamic",
         "-j", ".rodata", "-j", ".rel", "-j", ".rela", "-j", ".rel.*",
         "-j", ".rela.*", "-j", ".rel*", "-j", ".rela*", "-j", ".areloc",
         "-j", ".reloc", "-O", "efi-app-%s" % EFI_ARCH, so, efi])
    # arrival check: the objcopy step above runs with check=True
    checks.check(os.path.isfile(efi), "objcopy did not produce an EFI image")

    with open(efi, "rb") as handle:
        image = handle.read()
    checks.check(image[:2] == b"MZ", "EFI image has no DOS/PE magic")
    pe = struct.unpack_from("<I", image, 0x3C)[0]
    checks.check(image[pe:pe + 4] == b"PE\x00\x00", "EFI image has no PE signature")
    machine = struct.unpack_from("<H", image, pe + 4)[0]
    checks.check(machine == PE_MACHINE_AARCH64,
                 "machine=0x%x, expected 0x%x" % (machine, PE_MACHINE_AARCH64))
    subsystem = struct.unpack_from("<H", image, pe + 0x5C)[0]
    checks.check(subsystem == EFI_APPLICATION_SUBSYSTEM,
                 "subsystem=%d, expected %d" % (subsystem, EFI_APPLICATION_SUBSYSTEM))

    checks.report()
    print("gnu-efi consumer test OK: %s (%d bytes, PE32+ aarch64 EFI application)"
          % (efi, len(image)))


if __name__ == "__main__":
    main()
