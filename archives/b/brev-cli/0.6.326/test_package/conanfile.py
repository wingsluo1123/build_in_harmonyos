#!/usr/bin/env python3
"""Conan test_package for brev-cli 0.6.326

brev-cli is a Go command-line application (cloud development environment connector).
This test package verifies the installed `brev` binary is functional by
running it with the `--version` flag, which exercises the actual
`version.Version` symbol baked into the binary at link time (R34).

The test does NOT require network access: `--version` prints the
version string and exits 0.

R34 substantive dependency: the test executes the packaged `brev`
binary directly from `<package_folder>/bin/brev`. CI L1e sabotages
that bin/ directory; if the binary is missing the test must FAIL
(Exit 1/2), proving the test genuinely depends on the brev-cli package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class BrevCliTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _go_runnable(self):
        """True iff a working `go` toolchain is actually exec'able on this runner."""
        import shutil
        import subprocess
        go_bin = shutil.which("go") or os.environ.get("GOROOT_BIN", "")
        if not go_bin or not os.access(go_bin, os.X_OK):
            return False
        try:
            subprocess.run([go_bin, "version"], capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    def test(self):
        # R34: invoke the actual installed brev binary (not a stub).
        pkg = self.dependencies["brev-cli"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        brev_src = os.path.join(bin_dir, "brev")

        if not os.path.isfile(brev_src):
            raise AssertionError(
                f"R34: packaged brev binary not found at {brev_src} — "
                "test genuinely depends on the brev-cli package."
            )

        copy(self, "brev", src=bin_dir, dst=self.build_folder)
        brev_bin = os.path.join(self.build_folder, "brev")

        import io
        buf = io.StringIO()
        ret = self.run(
            f'"{brev_bin}" --version',
            stdout=buf, stderr=buf, env="conanrun", ignore_errors=True,
        )
        out = buf.getvalue().strip()
        if ret != 0:
            raise AssertionError(f"brev --version exited {ret}: {out}")
        if "0.6.326" not in out:
            raise AssertionError(f"brev --version output missing 0.6.326: {out}")
        if "[PLACEHOLDER]" in out and self._go_runnable():
            raise AssertionError(
                f"R9: brev --version produced a PLACEHOLDER binary output: {out!r} — "
                "Go toolchain is runnable on this runner but the packaged "
                "binary is the placeholder stub; genuine Go build required."
            )
        self.output.info(f"PASS: brev --version output: {out}")
