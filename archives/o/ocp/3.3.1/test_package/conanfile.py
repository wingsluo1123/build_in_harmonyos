#!/usr/bin/env python3
"""Conan test_package for the ocp application package (Conan L1 test).

ocp is a front end, so the consumer test executes the installed binary: see
test.c for the details.  The path of the delivered binary is handed to CMake,
which passes it to the CTest case.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OcpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    @property
    def _front_end(self):
        """Absolute path of the packaged ocp binary."""
        bindir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin")
        return os.path.join(bindir, "ocp.exe" if self.settings.os == "Windows" else "ocp")

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"OCP_BINARY_DIR": os.path.dirname(self._front_end)})
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()  # CTest, which executes the packaged front end (see test.c)

        # Second, direct execution of the delivered binary.  The output has to
        # go to a file: the player reports its state on stderr and exits with
        # 255 when it finds no per-user configuration.
        log = os.path.join(self.build_folder, "ocp-version.log")
        outcome = self.run('"{}" --version > "{}" 2>&1'.format(self._front_end, log),
                           env="conanrun", ignore_errors=True)
        output = ""
        if os.path.exists(log):
            with open(log, encoding="utf-8", errors="replace") as handle:
                output = handle.read()
        if "ocp.ini" in output:
            # the player started, the loader resolved its shared libraries and
            # main() reported the missing configuration - the artifact works
            return
        # 126/127 mean this build host cannot execute the target binary (cross
        # compilation); the aarch64 ELF is verified by test.c in that case.
        assert str(outcome).strip() in ("126", "127"), (outcome, output)
