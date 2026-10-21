#!/usr/bin/env python3
"""Conan test_package for pixelize 2.0.0-git20220108.d1f9da9 — consumer
verification.

Runs the real installed `pixelize` + `make_db` through test.sh (6
behavioral assertions) plus an ELF gate on both binaries:

  1) pixelize --help → rc=0, usage contains [image_file] (GOption handles
     --help before GTK display init → headless-safe)
  2) make_db --help → rc=0, usage contains [FILE...]
  3) pixelize --no-such-option → GOption rejects → main() else-branch
     "Error: in parameters" + exit(1)
  4) make_db --no-such-option → same negative path
  5) pixelize without a display (broadway backend, no broadwayd) →
     gtk_init_with_args fails at display open → same else-branch exit(1)
     (almanah/0.12.4-style headless negative assertion; also proves the
     whole gtk/glib/gdk-pixbuf/pango/cairo dynamic chain resolves)
  6) make_db without a display → same
  ELF gate: both packaged binaries must be aarch64 ELF (e_machine 0xB7,
  matches settings arch=armv8).

Execution model: identical to vimpc/0.09.2, musicpc/0.35, tasksh/1.2.0,
array-hash/0.7.2 — decided from the ELF header of the produced binary,
NOT from Conan cross_building(): the OHOS profiles pass the same file for
-pr:h and -pr:b, so Conan reports host == build even though the ELF is
foreign. On a foreign-architecture host (x86_64 Linux dev box
cross-building for OHOS aarch64) test.sh launches the binaries through
qemu-aarch64 against the OHOS guest sysroot with the fortify/compat
shims preloaded in the guest (they provide __strlen_chk() and friends
plus arc4random()/arc4random_buf(), which the emulated guest libc —
upstream musl — does not implement).
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
# Guest-side fortify/compat shims: the OHOS-fortified binaries and their
# dependencies (gtk/pango/cairo/expat) reference __*_chk() and arc4random*()
# symbols that the emulated guest libc (upstream musl) does not provide.
# Preloaded into the guest via -E LD_PRELOAD (musl ldso separator: ':').
_GUEST_PRELOAD = (
    "libchkfcnshim.so",     # __strlen_chk/__strcat_chk/__fread_chk/...
    "libmemchrchkshim.so",  # __memchr_chk
    "libpcmchkshim.so",     # __memcpy_chk/__memset_chk
    "libarc4shim.so",       # arc4random/arc4random_buf
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


class PixelizeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _emulation_env(self, bin_path):
        """Empty on the CI worker (the ELF is native there). On a
        cross-build host it names qemu-aarch64, the guest sysroot and the
        fortify/compat shims, which test_package/test.sh turns into the
        actual qemu command line."""
        if _elf_machine(bin_path) == _host_machine():
            return {}
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise Exception(
                "the packaged pixelize ELF targets a foreign architecture "
                "and qemu-aarch64 is required to execute it under test")
        guest = next((root for root in _GUEST_ROOTS
                      if os.path.isdir(os.path.join(root, "lib"))), None)
        if guest is None:
            raise Exception(
                "the packaged pixelize ELF targets a foreign architecture "
                f"and no OHOS guest sysroot was found in {list(_GUEST_ROOTS)}")
        env = {"PIXELIZE_RUNNER": qemu,
               "PIXELIZE_GUEST_ROOT": guest,
               "PIXELIZE_CROSS_EMULATED": "1"}
        shims = [os.path.join(guest, "lib", name) for name in _GUEST_PRELOAD]
        shims = [path for path in shims if os.path.isfile(path)]
        if shims:
            env["PIXELIZE_GUEST_PRELOAD"] = ":".join(shims)
        return env

    def test(self):
        dep = self.dependencies["pixelize"]
        bindir = dep.cpp_info.bindirs[0]
        pixelize_bin = os.path.join(bindir, "pixelize")
        makedb_bin = os.path.join(bindir, "make_db")
        for binary in (pixelize_bin, makedb_bin):
            if not os.path.isfile(binary):
                raise Exception(f"missing packaged binary: {binary}")
            # ELF gate: packaged binaries must be aarch64 ELF (settings
            # arch=armv8); a wrong-arch artifact must fail the test.
            machine = _elf_machine(binary)
            if machine != _EM_AARCH64:
                raise Exception(
                    f"{binary} is not an aarch64 ELF "
                    f"(e_machine={machine}, expected {_EM_AARCH64})")
        env = self._emulation_env(pixelize_bin)
        sh = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or shutil.which("sh") or "/bin/sh"

        def q(s):
            return '"' + s.replace('"', '\\"') + '"'

        test_sh = os.path.join(self.source_folder, "test.sh")
        cmd = " ".join([q(sh), q(test_sh), q(pixelize_bin), q(makedb_bin)])
        if env:
            # ConanFile.run() has no env_append parameter; pass the
            # cross-emulation variables as a command prefix instead.
            env_prefix = " ".join(f"{k}={q(v)}" for k, v in sorted(env.items()))
            cmd = f"{env_prefix} {cmd}"
        self.run(cmd, env="conanrun")
