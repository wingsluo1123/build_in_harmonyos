#!/usr/bin/env python3
"""Conan test_package for urjtag 2021.03.

Executes the packaged OHOS binaries (jtag / bsdl2jtag) and checks their real
behaviour:

* command-line contract of both tools (version, help/usage, exit codes)
* a real JTAG-script run: ``jtag -n`` executes a script file (``help`` +
  ``quit``) through the packaged command parser/dispatch loop - no JTAG
  hardware involved; the command list must contain the statically linked
  ``svf`` and ``bsdl`` command modules
* HarmonyOS-specific checks: aarch64 OHOS PIE ELF, OHOS musl
  loader/interpreter (both coexisting loader names accepted, glibc loader
  rejected), DT_NEEDED wiring (OHOS libc.so + libusb-1.0.so, no glibc-only
  sonames, no absolute paths), the packaged static library liburjtag.a
  (ar archive with aarch64 ELF members), installed headers + part database

How the packaged binaries are started (see ``_emulator_prefix``):

  1. directly - on a real OHOS machine the binaries just run, and the CI
     gate builds with the ``ohos-aarch64`` profile on both sides (host and
     build), so ``can_run()`` is true there and binfmt/qemu-aarch64 (where
     registered) executes them transparently.  The runtime library paths
     (libusb-1.0.so) come from the conanrun environment.
  2. through ``qemu-aarch64 -L <guest sysroot>`` on a cross host, with the
     guest rootfs' aarch64 fortify shims preloaded into the guest through
     ``QEMU_SET_ENV``: the OHOS ``<sys/select.h>`` makes ``FD_SET`` /
     ``FD_ISSET`` call the musl fortify helper ``__fd_chk``.  The OHOS
     device libc exports it, but the generic local musl loader that
     qemu-user starts does not, so a freshly packaged binary otherwise dies
     during relocation with
     ``Error relocating ...: __fd_chk: symbol not found``.
     ``QEMU_SET_ENV`` is interpreted by qemu-user and applied to the guest
     process only, so the aarch64 shims never reach the x86_64 host
     processes (a host-side ``LD_PRELOAD`` would make the qemu process
     itself fail with "wrong ELF class") - same technique as
     archives/y/yosys/0.66; knowledge draft
     DRAFT-yosys-0.66-ohos-aarch64-local-run-missing-fd-chk.
"""

import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment

# aarch64 fortify shims a local OHOS guest rootfs ships in lib/; mirrored
# from test_urjtag.py (which injects the same list for the commands it runs
# itself).  The OHOS device libc provides all of these natively - they only
# exist to satisfy the generic local musl loader used by qemu-user.
GUEST_SHIM_NAMES = (
    "libfdchkshim.so",
    "libchkfcnshim.so",
    "libmemchrchkshim.so",
    "libpcmchkshim.so",
    "libmprotshim.so",
    "libmallinfo2shim.so",
    "libarc4shim.so",
)


class UrjtagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _executable(self, name):
        dependency = self.dependencies["urjtag"]
        path = os.path.join(dependency.cpp_info.bindirs[0], name)
        if not os.path.isfile(path):
            raise ConanException(f"missing packaged executable: {path}")
        return path

    def _sysroot_candidates(self):
        """Guest rootfs candidates, most specific first."""
        return [
            os.environ.get("OHOS_SYSROOT", ""),
            os.environ.get("OHC_OHOS_SYSROOT", ""),
            "/opt/ohos-guest",
            "/opt/ohos-toolchain/sysroot",
        ]

    def _guest_shims(self, sysroot):
        """``LD_PRELOAD`` list of the aarch64 shims shipped in a guest rootfs."""
        libdir = os.path.join(sysroot, "lib")
        if not os.path.isdir(libdir):
            return ""
        shims = [
            os.path.join(libdir, name)
            for name in GUEST_SHIM_NAMES
            if os.path.isfile(os.path.join(libdir, name))
        ]
        return ":".join(shims)

    def _run_variants(self, emulator):
        """Yield ``(prefix, qemu_set_env)`` candidates, least intrusive first.

        A real OHOS runner (or a host with a complete OHOS rootfs) needs
        nothing but the emulator; the cross machine needs the guest sysroot
        for the loader and libusb, and the fortify shims for ``__fd_chk``.
        """
        yield [emulator], ""
        for sysroot in self._sysroot_candidates():
            if sysroot and os.path.isdir(sysroot):
                yield [emulator, "-L", sysroot], ""
        for sysroot in self._sysroot_candidates():
            if sysroot and os.path.isdir(sysroot):
                shims = self._guest_shims(sysroot)
                if shims:
                    yield [emulator, "-L", sysroot], f"LD_PRELOAD={shims}"

    def _run(self, command, qemu_set_env):
        """Run a command, optionally injecting the qemu guest environment.

        ``QEMU_SET_ENV`` is interpreted by qemu-user and applied to the
        guest process only, so the aarch64 shims never reach the x86_64
        host processes (clang/make/qemu itself).
        """
        if qemu_set_env:
            env = Environment()
            env.define("QEMU_SET_ENV", qemu_set_env)
            with env.vars(self).apply():
                self.run(command, env="conanrun")
        else:
            self.run(command, env="conanrun")

    def _emulator_prefix(self, probe_executable):
        """Return ``(prefix, qemu_set_env)`` needed to run the packaged binaries.

        The combination is selected by running ``jtag --version``: jtag is
        the only packaged tool with a zero-exit ``--version`` contract -
        bsdl2jtag prints its usage and exits 1 for every invocation
        (asserted as check 3 of test_urjtag.py), so it cannot be used to
        probe the emulator.
        """
        # 1) direct execution: real OHOS machine, or a cross host with
        #    binfmt registered (the CI gate's ohos-aarch64 profile on both
        #    sides makes conan treat the target as runnable).
        try:
            self._run(shlex.join([probe_executable, "--version"]), "")
            return [], ""
        except ConanException:
            pass
        # 2) qemu-user on a cross host.
        emulator = shutil.which("qemu-aarch64")
        if not emulator:
            raise ConanException(
                "the packaged OHOS aarch64 binaries cannot be executed "
                "here: direct execution failed and qemu-aarch64 is not "
                "available"
            )
        for prefix, qemu_set_env in self._run_variants(emulator):
            try:
                self._run(
                    shlex.join([*prefix, probe_executable, "--version"]),
                    qemu_set_env,
                )
                return prefix, qemu_set_env
            except ConanException:
                continue
        raise ConanException(
            "qemu-aarch64 could not run the packaged OHOS binary; "
            "checked prefixes: "
            + ", ".join(
                " ".join(prefix) + (f" [QEMU_SET_ENV={env}]" if env else "")
                for prefix, env in self._run_variants(emulator)
            )
        )

    def test(self):
        jtag_exe = self._executable("jtag")
        prefix, qemu_set_env = self._emulator_prefix(jtag_exe)
        jtag = [*prefix, jtag_exe]
        bsdl2jtag = [*prefix, self._executable("bsdl2jtag")]
        self._run(shlex.join(jtag + ["--version"]), qemu_set_env)
        self._run(shlex.join(jtag + ["--help"]), qemu_set_env)
        dependency = self.dependencies["urjtag"]
        script = os.path.join(self.source_folder, "test_urjtag.py")
        self._run(
            shlex.join(
                [
                    sys.executable,
                    script,
                    "--jtag",
                    *jtag,
                    "--bsdl2jtag",
                    *bsdl2jtag,
                    "--pkgroot",
                    dependency.package_folder,
                ]
            ),
            qemu_set_env,
        )
        self.output.info("urjtag offline smoke test passed")
