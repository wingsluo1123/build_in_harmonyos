#!/usr/bin/env python3
"""Conan test_package for hyperfine 1.20.0-r0 — static smoke test.

hyperfine is a command-line benchmarking tool. This test verifies the
packaged `hyperfine` binary's integrity through static checks via
test_smoke.sh.

The binary is NOT executed: on HarmonyOS the musl dynamic linker does not
support LD_LIBRARY_PATH/RPATH/RUNPATH, and the precompiled Alpine musl
binary requires libgcc_s.so.1 (providing _Unwind_* symbols) which is not
available in any system library search path. This is a known platform
limitation (E072: rustc SIGSEGV on musl; Alpine precompiled binary needs
libgcc_s.so.1 not in system paths).

R34: The test substantively depends on the hyperfine package by verifying
the packaged binary's existence, ELF format, architecture, NEEDED entries,
and size. CI L1e sabotages bin/ — if the binary is missing, the test FAILS.
"""
import os
import shutil

from conan import ConanFile


class HyperfineTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: verify the packaged hyperfine binary from the package.
        pkg = self.dependencies["hyperfine"]
        pkg_folder = pkg.package_folder
        test_script = os.path.join(self.source_folder, "test_smoke.sh")
        if not os.path.isfile(test_script):
            raise Exception(f"test source not found: {test_script}")

        sh = (os.environ.get("CONFIG_SHELL")
              or shutil.which("sh")
              or "/system/bin/sh")

        # Execute the test source: static assertions on the packaged artifact
        self.run(
            f'"{sh}" "{test_script}" "{pkg_folder}"',
            env="conanrun",
        )
