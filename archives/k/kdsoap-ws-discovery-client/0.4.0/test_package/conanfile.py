#!/usr/bin/env python3
"""Exercise the installed KDSoap WS-Discovery CMake target and OHOS UDP path."""

import os
import platform

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class KDSoapWSDiscoveryClientTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        qtbase = self.dependencies["qtbase"]
        kdsoap = self.dependencies["kdsoap"]
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        qt_cmake = os.path.join(qtbase.package_folder, "lib", "cmake")
        for component in ("Qt6", "Qt6Core", "Qt6CoreTools", "Qt6Network", "Qt6Xml"):
            tc.cache_variables[f"{component}_DIR"] = os.path.join(qt_cmake, component)
        tc.cache_variables["KDSoap-qt6_DIR"] = os.path.join(
            kdsoap.package_folder, "lib", "cmake", "KDSoap-qt6"
        )
        tc.cache_variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self) and platform.system() == "HarmonyOS":
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 30 -j1'.format(
                    self.build_folder
                ),
                env=["conanrun"],
            )
            self.output.info("KDSOAP_WSD_CONSUMER_AND_HARMONYOS_LOOPBACK_PASS")
