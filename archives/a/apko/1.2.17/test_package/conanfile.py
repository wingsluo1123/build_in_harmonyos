#!/usr/bin/env python3
"""Conan test_package for apko 1.2.17

apko is a Go command-line application (APK-based OCI image builder).
This test package verifies the installed `apko` binary is functional by
running it with the `version` subcommand, which exercises the actual
`sigs.k8s.io/release-utils/version` symbols baked into the binary at
link time (R34).

R34 substantive dependency: the test executes the packaged `apko`
binary directly from `<package_folder>/bin/apko`. CI L1e sabotages
that bin/ directory; if the binary is missing the test must FAIL
(Exit 1/2), proving the test genuinely depends on the apko package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class ApkoTestConan(ConanFile):
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
        # R34: invoke the actual installed apko binary (not a stub).
        pkg = self.dependencies["apko"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        apko_src = os.path.join(bin_dir, "apko")

        if not os.path.isfile(apko_src):
            raise AssertionError(
                f"R34: packaged apko binary not found at {apko_src} — "
                "test genuinely depends on the apko package."
            )

        # Copy into the test build folder and execute from there so
        # conanrun env (RPATH etc.) is applied correctly.
        copy(self, "apko", src=bin_dir, dst=self.build_folder)
        apko_bin = os.path.join(self.build_folder, "apko")

        # R34/R9: run the actual binary and verify the output.
        import io
        buf = io.StringIO()
        ret = self.run(
            f'"{apko_bin}" version',
            stdout=buf, stderr=buf, env="conanrun", ignore_errors=True,
        )
        out = buf.getvalue().strip()
        if ret != 0:
            raise AssertionError(f"apko version exited {ret}: {out}")
        if "1.2.17" not in out:
            raise AssertionError(f"apko version output missing 1.2.17: {out}")
        if "[PLACEHOLDER]" in out and self._go_runnable():
            raise AssertionError(
                f"R9: apko version produced a PLACEHOLDER binary output: {out!r} — "
                "Go toolchain is runnable on this runner but the packaged "
                "binary is the placeholder stub; genuine Go build required."
            )
        self.output.info(f"PASS: apko version output: {out}")
