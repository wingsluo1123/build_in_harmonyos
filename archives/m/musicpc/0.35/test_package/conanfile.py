#!/usr/bin/env python3
"""Conan test_package for musicpc 0.35 (mpc).

Runs the packaged `mpc` ELF for real: four consumer assertions that need no
MPD server (unknown-command error + compiled-in version string, the help
command table, and two paths that reach the libmpdclient connection layer).

Execution model
---------------
CI runs this on a real HarmonyOS PC worker, where the OHOS aarch64 ELF is
native: test.sh execs the binary directly. On a host whose architecture
differs from the packaged ELF (e.g. an x86_64 Linux dev box compiling for
OHOS aarch64) the binary cannot be exec'd. The decision is taken from the
ELF header of the produced binary, NOT from Conan's cross_building(): the
OHOS profiles pass the same file for -pr:h and -pr:b, so Conan reports
host == build even though the ELF is foreign. In that case test.sh launches
the binary through qemu-aarch64 against an OHOS guest sysroot with the
fortify shim preloaded in the guest (the shim provides __fd_chk(), which
the emulated guest libc does not implement). Precedent:
archives/t/tasksh/1.2.0, archives/a/array-hash/0.7.2.
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
# Guest-side fortify shim: OHOS headers reference __fd_chk(), which the
# emulated guest libc does not provide.
_GUEST_PRELOAD = "libfdchkshim.so"


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


class MusicpcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _emulation_env(self, mpc_bin):
        """Empty on the CI worker (the ELF is native there). On a cross-build
        host it names qemu-aarch64, the guest sysroot and the fortify shim,
        which test_package/test.sh turns into the actual qemu command line.
        `cross_building()` is deliberately not consulted: the OHOS profiles
        pass the same file for -pr:h and -pr:b, so Conan sees host == build
        even though the ELF is aarch64 and the host is x86_64."""
        if _elf_machine(mpc_bin) == _host_machine():
            return {}
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise Exception(
                "the packaged mpc ELF targets a foreign architecture and "
                "qemu-aarch64 is required to execute it under test")
        guest = next((root for root in _GUEST_ROOTS
                      if os.path.isdir(os.path.join(root, "lib"))), None)
        if guest is None:
            raise Exception(
                "the packaged mpc ELF targets a foreign architecture and no "
                f"OHOS guest sysroot was found in {list(_GUEST_ROOTS)}")
        env = {"MPC_RUNNER": qemu,
               "MPC_GUEST_ROOT": guest,
               "MPC_CROSS_EMULATED": "1"}
        preload = os.path.join(guest, "lib", _GUEST_PRELOAD)
        if os.path.isfile(preload):
            env["MPC_GUEST_PRELOAD"] = preload
        return env

    def test(self):
        # The test logic itself is host shell: sh, timeout and grep all run
        # natively. Only the mpc binary goes through the emulation prefix,
        # which is why the qemu command line is built inside test.sh.
        sh = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or shutil.which("sh") or "/bin/sh"
        mpc_bin = os.path.join(
            self.dependencies["musicpc"].cpp_info.bindirs[0], "mpc")
        env = self._emulation_env(mpc_bin)

        def q(s):
            return '"' + s.replace('"', '\\"') + '"'

        cmd = " ".join([q(sh),
                        q(os.path.join(self.source_folder, "test.sh")),
                        q(mpc_bin)])
        if env:
            # ConanFile.run() has no env_append parameter; pass the
            # cross-emulation variables as a command prefix instead.
            env_prefix = " ".join(
                f"{k}={q(v)}" for k, v in sorted(env.items()))
            cmd = f"{env_prefix} {cmd}"
        self.run(cmd, env="conanrun")
