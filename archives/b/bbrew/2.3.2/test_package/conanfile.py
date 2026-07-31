#!/usr/bin/env python3
"""Conan test_package for bbrew 2.3.2

bbrew is a Go command-line application (Bold Brew TUI for Homebrew).
This test package verifies the installed `bbrew` binary is functional by
running it with the `--version` flag, which exercises the actual
`services.AppVersion` symbol baked into the binary at link time (R34).

The test does NOT require Homebrew to be installed: `--version` prints the
version string and exits 0 without touching the TUI or Homebrew data.

R34 substantive dependency: the test executes the packaged `bbrew`
binary directly from `<package_folder>/bin/bbrew`. CI L1e sabotages
that bin/ directory; if the binary is missing the test must FAIL
(Exit 1/2), proving the test genuinely depends on the bbrew package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class BbrewTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: invoke the actual installed bbrew binary (not a stub).
        # Resolve the binary path from the packaged bin/ directory so
        # that L1e sabotage (moving bin/ away) makes this test FAIL.
        pkg = self.dependencies["bbrew"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        bbrew_src = os.path.join(bin_dir, "bbrew")

        if not os.path.isfile(bbrew_src):
            # The packaged binary is missing — this is exactly what L1e
            # sabotage does. A genuine R34 test must fail hard here.
            raise AssertionError(
                f"R34: packaged bbrew binary not found at {bbrew_src} — "
                "test genuinely depends on the bbrew package."
            )

        # Copy into the test build folder and execute from there so
        # conanrun env (RPATH etc.) is applied correctly.
        copy(self, "bbrew", src=bin_dir, dst=self.build_folder)
        bbrew_bin = os.path.join(self.build_folder, "bbrew")

        # R34/R9: run the actual binary and verify the output. Capture
        # stdout/stderr so a placeholder artifact (emitted by
        # conanfile.py._build_placeholder() when the Go toolchain is
        # unavailable) is detected and FAILS the test — a placeholder
        # must never pass as a genuine Go build (R9: no fake pass).
        import subprocess
        proc = subprocess.run(
            [bbrew_bin, "--version"], capture_output=True, text=True, timeout=30
        )
        out = (proc.stdout + proc.stderr).strip()
        if "[PLACEHOLDER]" in out:
            raise AssertionError(
                f"R9: bbrew --version produced a PLACEHOLDER binary output: {out!r} — "
                "Go toolchain unavailable on this runner; genuine Go build required."
            )
        if proc.returncode != 0:
            raise AssertionError(f"bbrew --version exited {proc.returncode}: {out}")
        if "2.3.2" not in out:
            raise AssertionError(f"bbrew --version output missing 2.3.2: {out}")
        self.output.info(f"PASS: bbrew --version output: {out}")
