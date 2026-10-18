#!/usr/bin/env python3
"""test_package - PLAST 2.3.2 consumer test.

Two independent checks are performed by test():

  * test_plast_api - a C++ program built against the *installed* package that
    drives the algorithm through the public library API
    (launcher::core::PlastOptionsParser + launcher::core::PlastCmd), i.e. the
    same code path the shipped PlastCmd binary uses;
  * test.sh - an end-to-end run of the packaged PlastCmd / makeplastdb
    binaries on small FASTA fixtures, including a negative control that must
    not produce a high identity alignment.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PlastTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeDeps exposes plast::plast.  The packaged executables are passed to
    # the test script by path, so VirtualRunEnv is not what makes them runnable.
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        cmake = CMakeToolchain(self)
        # Same E092 mapping as the recipe: CMake has no HarmonyOS platform
        # module, and this test code is platform agnostic.
        cmake.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        cmake.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # E074 / P020: HMDFS has no mkfifo, so GNU make cannot set up its
        # jobserver; force a single job (same reason as the recipe itself).
        cmake.build(build_tool_args=["-j1"])

    def _bash(self):
        """Locate a bash able to run test.sh.

        OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so the script
        has to be driven through a real bash.  Its location is device specific
        (/data/service/hnp/bin/bash on the shadow CI toolchain, ~/usr/local/bin
        on a plain device), hence the lookup.
        """
        candidates = [
            shutil.which("bash"),
            os.environ.get("CONFIG_SHELL"),
            os.path.join(os.path.expanduser("~"), "usr/local/bin/bash"),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def test(self):
        if not can_run(self):
            return

        api_test = os.path.join(self.build_folder, "test_plast_api")
        if not os.path.exists(api_test):
            # multi-configuration generators nest the binaries per config
            api_test = os.path.join(self.build_folder, str(self.settings.build_type),
                                    "test_plast_api")

        # The packaged PlastCmd / makeplastdb are handed over explicitly instead
        # of relying on the generated run environment to extend PATH: that is
        # what actually runs them on the device.
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder

        self.run(
            f'"{self._bash()}" "{os.path.join(self.source_folder, "test.sh")}" '
            f'"{os.path.join(self.source_folder, "data")}" '
            f'"{api_test}" '
            f'"{os.path.join(pkg_folder, "bin")}"',
            env="conanrun",
        )
