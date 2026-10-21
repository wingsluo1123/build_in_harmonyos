#!/usr/bin/env python3
"""Conan test_package for xlockmore 5.89 (application package).

Consumer verification (R34 anti-stub), in two layers:

1. Structural (always, strict): the packaged ``bin/xlock`` must exist, be
   non-empty and be a valid AArch64 ELF executable.  Read directly from
   the package folder, so it also makes the gate's L1e destructive
   negative test work: when the gate moves ``bin/`` away, this check
   fails and ``conan test`` is non-zero, exactly as R34 requires.

2. Runtime (always): ``test_xlock.sh`` launches the packaged binary with
   ``-help`` through the conanrun environment (packaged ``bin/`` on PATH,
   every dependency ``lib/`` on LD_LIBRARY_PATH).  The dynamic loader
   resolves every DT_NEEDED entry (libX11.so.6, libXext.so.6,
   libXmu.so.6, libXt, libSM, libICE, ...) before main(); the printed
   usage banner proves the binary genuinely ran, and any loader error is
   rejected by the script.

Execution model (precedent: archives/x/xdx/2.91):
The native/emulated decision is taken from the ELF header of the produced
binary, NOT from Conan's cross_building(): the OHOS profiles pass the same
file for -pr:h and -pr:b, so Conan reports host == build even though the
ELF is foreign to an x86_64 dev box.

  * native   — the ELF matches the build host (the CI case: an OpenHarmony
               PC aarch64 worker).  Exec it directly.
  * emulated — an x86_64 Linux box building for OHOS aarch64.  Exec it
               under qemu-aarch64 against the OHOS guest sysroot
               (/opt/ohos-guest) plus the guest-side shims, which cover
               the glibc-fortify (__*_chk) and arc4random references in
               the prebuilt registry X libraries that the emulated guest
               libc does not provide.
"""
import os
import platform
import shutil
import struct

from conan import ConanFile

# e_machine values from the ELF spec, restricted to what matters here.
_EM_AARCH64 = 0xB7
_EM_X86_64 = 0x3E

# Guest sysroots searched for the OHOS loader/libc when emulating.
_GUEST_ROOTS = ("/opt/ohos-guest",)
# Guest-side shims (all under <guest>/lib): the emulated OHOS libc lacks
# the glibc-fortify __*_chk family and arc4random referenced by the
# prebuilt X dependency stack (libX11/libICE/libXdmcp).  Preloading them
# makes the full dependency closure resolve under qemu, exactly as the
# OHOS runtime provides it on-device.
_GUEST_PRELOADS = (
    "libchkfcnshim.so",    # __fd_chk __fread_chk __fwrite_chk ...
    "libfdchkshim.so",     # __fd_chk family
    "libpcmchkshim.so",    # __memcpy_chk __memset_chk
    "libmemchrchkshim.so", # __memchr_chk
    "libarc4shim.so",      # arc4random arc4random_buf
    "libmallinfo2shim.so", # mallinfo2
)


def _elf_machine(path):
    """Return the ELF e_machine of `path`, or None if it is not an ELF."""
    with open(path, "rb") as handle:
        header = handle.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        return None
    little_endian = header[5] == 1
    return struct.unpack("<H" if little_endian else ">H", header[18:20])[0]


def _host_machine():
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return _EM_AARCH64
    if machine in ("x86_64", "amd64"):
        return _EM_X86_64
    return None


class XlockmoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test_xlock.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _emulation_env(self, xlock_bin):
        """Environment for executing a foreign-architecture xlock ELF.

        Empty on the CI worker (the ELF is native there).  On a cross-build
        host it names qemu-aarch64, the guest sysroot and the guest-side
        shims, which test_xlock.sh turns into the actual qemu command line.
        """
        if _elf_machine(xlock_bin) == _host_machine():
            return {}

        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise Exception(
                "the packaged xlock ELF targets a foreign architecture and "
                "qemu-aarch64 is required to execute it under test")
        guest = next((root for root in _GUEST_ROOTS
                      if os.path.isdir(os.path.join(root, "lib"))), None)
        if guest is None:
            raise Exception(
                "the packaged xlock ELF targets a foreign architecture and no "
                f"OHOS guest sysroot was found in {list(_GUEST_ROOTS)}")
        preload = ":".join(
            os.path.join(guest, "lib", name) for name in _GUEST_PRELOADS
            if os.path.isfile(os.path.join(guest, "lib", name)))
        if not preload:
            raise Exception(
                "guest sysroot found but none of the expected shims exist")
        return {"XL_RUNNER": qemu,
                "XL_GUEST_ROOT": guest,
                "XL_GUEST_PRELOAD": preload}

    def _structural_check(self, xlock_bin):
        if not os.path.isfile(xlock_bin):
            raise RuntimeError(
                "FAIL structural: packaged bin/xlock missing "
                "(package bin/ moved away?)")
        if os.path.getsize(xlock_bin) == 0:
            raise RuntimeError("FAIL structural: packaged bin/xlock is empty")
        machine = _elf_machine(xlock_bin)
        if machine != _EM_AARCH64:
            raise RuntimeError(
                "FAIL structural: bin/xlock e_machine=0x%x, expected 0xb7 "
                "(EM_AARCH64)" % (machine or 0))
        self.output.info(
            "structural OK: bin/xlock exists, non-empty, AArch64 ELF")

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        xlock_bin = os.path.join(pkg.package_folder, "bin", "xlock")
        self._structural_check(xlock_bin)

        env = self._emulation_env(xlock_bin)

        def q(s):
            return '"' + s.replace('"', '\\"') + '"'

        cmd = " ".join([q("sh"),
                        q(os.path.join(self.source_folder, "test_xlock.sh"))])
        if env:
            # ConanFile.run() has no env_append parameter; pass the
            # cross-emulation variables as a command prefix instead.
            env_prefix = " ".join(
                f"{k}={q(v)}" for k, v in sorted(env.items()))
            cmd = f"{env_prefix} {cmd}"
        self.run(cmd, env="conanrun")
