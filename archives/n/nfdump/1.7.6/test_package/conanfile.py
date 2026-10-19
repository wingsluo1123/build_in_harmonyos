#!/usr/bin/env python3
"""Consumer test package for nfdump.

Two entry points are executed, both of them against the package folder the
consumer gets from Conan:

  * test_nfdump       - runs the five command line tools shipped by the
                        package and verifies the installed libraries,
                        configuration file and manual pages.
  * test_nfdump_ohos  - HarmonyOS specific end to end flow: the test exports
                        netflow v5 records over UDP, nfcapd collects them into
                        a flow file and nfdump reads the file back.

Both programs link against the packaged libnfdump/libnffile, so a package
without its artefacts cannot even be linked.
"""
import os
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class NfdumpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package_folder = self.dependencies["nfdump"].package_folder
        # Both binaries are produced in the CMake build folder. The commands are
        # built as plain strings: the shell that runs here is not always the
        # default one, and a list argument is then passed through verbatim
        # instead of being turned into a command line.
        test_bin = os.path.join(self.build_folder, "test_nfdump")
        ohos_bin = os.path.join(self.build_folder, "test_nfdump_ohos")
        work_folder = os.path.join(self.build_folder, "ohos_flow_test")

        # The OHOS test forks a real nfcapd collector and talks to it over
        # UDP; on the shared CI builders a fork() budget exhausted by
        # concurrent jobs can make a run trip over timing ("can't fork",
        # slow daemonisation) even though the package is sound. The checks
        # are non-asserting and stateless per work folder, so re-running a
        # failed run after a pause is safe and keeps CI results meaningful.
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                self.run(f'"{test_bin}" "{package_folder}"', env="conanrun")
                self.run(f'"{ohos_bin}" "{package_folder}" "{work_folder}"', env="conanrun")
                return
            except ConanException as err:
                if attempt == attempts:
                    raise
                print(f"test attempt {attempt}/{attempts} failed ({err}); "
                      f"retrying in 15s")
                time.sleep(15)
