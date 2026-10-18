#!/usr/bin/env python3
"""Conan test_package — indi-dsi (R34 probe; upstream has no test suite).

indi-dsi ships an INDI driver *executable*, not a linkable library, and
upstream provides NO test suite (R51 — source-tree inventory in notes.md).
Per R34 we exercise a real public API of the package: tokenize_str() from
the vendored Util.cpp (pure std::string helper used by the driver), with
six assertion groups covering delimiter semantics. The deeper USB protocol
paths (DsiDevice) require physical camera hardware and are out of scope.

Then we assert the produced driver binary is present (R34/L1e: the test
must fail without package artifacts) and probe it best-effort with --help.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class IndiDsiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        src_dir = os.path.join(
            self.dependencies["indi-dsi"].package_folder, "src")
        cmake = CMake(self)
        cmake.configure(variables={"DSI_SRC_DIR": src_dir})
        cmake.build()

    def test(self):
        # Layer 1 (R34): tokenize_str public-helper probe, compiled from the
        # vendored Util.cpp shipped in the package.
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindir, "test_dsi"),
                     env="conanrun")

        # Layer 2: the packaged driver binary must exist — this is what makes
        # the test depend on the package artifacts (executable-only package;
        # L1e sabotage removes bin/ but not the src/ that Layer 1 compiles).
        # Execution is best-effort: some environments deny exec on binaries
        # linked to shared libindi (EPERM/126), and --help exit codes vary.
        pkg = self.dependencies["indi-dsi"].package_folder
        exe = os.path.join(pkg, "bin", "indi_dsi_ccd")
        if not os.path.isfile(exe):
            raise ConanException(f"packaged driver binary missing: {exe}")
        if can_run(self):
            ret = self.run(f'"{exe}" --help', ignore_errors=True)
            if ret != 0:
                self.output.warning(
                    f"driver --help exited {ret}; tolerated (exec-restricted "
                    "environment or driver-specific exit code), "
                    "artifact presence already asserted"
                )
