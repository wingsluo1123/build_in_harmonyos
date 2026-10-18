#!/usr/bin/env python3
"""test_package for tsctp 0.8.6 — consumer run of the installed `tsctp` binary.

tsctp is an application (no headers / no library), so consumer verification is
"invoke the installed tool the way a user would":

  1. the binary is reachable through the package bin/ (Conan VirtualRunEnv PATH)
  2. the upstream CLI surface works (usage banner + option list, exit code 1)
  3. the SCTP code path really runs: server mode reaches socket(IPPROTO_SCTP);
     either the kernel accepts it (listener stays up) or it fails with the
     libc error text "Protocol not supported" — never a crash/signal.
  4. the static libsctp symbols are linked into the shipped binary (proof that
     the lksctp-tools dependency was consumed, not silently dropped).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class TsctpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building without emulator: test_package skipped")
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably;
        # wrap the test script with bash (same convention as the other
        # executable archives in this repository).
        if self.settings.os == "OHOS":
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            shell = shutil.which("bash") or "/bin/sh"
        self.run(f'"{shell}" test.sh', env="conanrun")
