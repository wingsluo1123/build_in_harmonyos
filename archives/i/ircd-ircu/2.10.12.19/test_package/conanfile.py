#!/usr/bin/env python3
"""Conan test_package for ircd-ircu 2.10.12.19 (Undernet IRC daemon).

ircd-ircu ships server binaries, so the test is a real end-to-end exercise of
the installed artifact (R34):

  1. `ircd -v` prints the compiled-in version banner and the compiled-in event
     engine list.
  2. `ircd -?` prints the usage text.
  3. `ircd -k` parses a generated configuration and reports "checked okay"
     (this drives the real config parser over the real shipped defaults).
  4. The daemon is started and a raw IRC client completes registration over
     TCP: NICK/USER in, RPL_WELCOME (001), RPL_MYINFO (004) and RPL_ISUPPORT
     (005) out, with 004 carrying the server version.
  5. QUIT is sent, the server closes the connection, and the listening port is
     released after a clean SIGTERM shutdown.

The shell is resolved at runtime: OHOS' /system/bin/sh is mksh and cannot run
ELF binaries nor provide bash's /dev/tcp, so bash is required. CI exports
CONFIG_SHELL=/data/service/hnp/bin/bash; locally /usr/bin/bash is used.

`build()` compiles droproot.c, a ~100 line launcher that hands the daemon an
unprivileged uid. ircd refuses to run as superuser (ircd.c returns 3), and the
OHOS worker runs as an unprivileged HMDFS uid while the local gate runs as root;
droproot passes the ids through untouched when they are already non-zero.

`test()` asserts the packaged artifacts exist before the `can_run()` guard, so
the test cannot pass without them (R34 / the gate's L1e reverse check), and
verifies the aarch64 ELF header when the binaries cannot be executed.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IrcdIrcuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    #: Artifacts this package must ship; the presence check below is what makes
    #: the test depend on the package (R34).
    REQUIRED_BINARIES = ("ircd", "umkpasswd", "convert-conf")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") or "clang"
        self.run(f"{cc} -O2 -Wall -o droproot droproot.c")

    def _bash(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            "bash",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            if os.path.sep in candidate:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
            else:
                for directory in os.environ.get("PATH", "").split(os.pathsep):
                    full = os.path.join(directory, candidate)
                    if os.path.isfile(full) and os.access(full, os.X_OK):
                        return full
        raise RuntimeError("no bash interpreter available to run test.sh")

    def test(self):
        # R34: assert the packaged artifacts exist BEFORE the can_run() guard.
        # `conan test` (what the gate's L1e destructive reverse check re-runs
        # after moving bin/ aside) passes a single -pr profile, so can_run() is
        # False there; a guard-only test would exit 0 and be reported as a fake
        # test. This mirrors archives/a/abbtr/1.0.4.
        package_folder = self.dependencies["ircd-ircu"].package_folder
        for binary in self.REQUIRED_BINARIES:
            path = os.path.join(package_folder, "bin", binary)
            if not os.path.isfile(path):
                raise RuntimeError(f"packaged artifact missing: {path}")
            if not os.access(path, os.X_OK):
                raise RuntimeError(f"packaged artifact is not executable: {path}")
        example_conf = os.path.join(package_folder, "ircd", "example.conf")
        if not os.path.isfile(example_conf):
            raise RuntimeError(f"packaged artifact missing: {example_conf}")
        self.output.info(f"all packaged artifacts present under {package_folder}")

        if can_run(self):
            self.run(f"{self._bash()} test.sh", env="conanrun")
            return

        # Cross-compiling: cannot execute the target binaries, so verify the
        # artifact is a real OHOS/aarch64 ELF instead of silently passing.
        ircd = os.path.join(package_folder, "bin", "ircd")
        with open(ircd, "rb") as handle:
            magic = handle.read(20)
        assert magic[:4] == b"\x7fELF", f"ircd is not an ELF binary: {magic!r}"
        assert magic[4] == 2, f"ircd is not 64-bit ELF (EI_CLASS={magic[4]})"
        assert magic[18] == 183, f"ircd is not EM_AARCH64 ELF (e_machine={magic[18]})"
        self.output.info(f"ircd is an aarch64 ELF and cross-compiling: {ircd}")