#!/usr/bin/env python3
"""Conan test_package — iceoryx 2.0.8 (consumer use case + form self check)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IceoryxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        iceoryx = self.dependencies["iceoryx"]
        default_shell = ("/data/service/hnp/bin/bash" if str(self.settings.os) == "OHOS"
                         else "/bin/sh")
        bash = os.environ.get("CONFIG_SHELL", default_shell)
        exe = os.path.join(self.build_folder, "test_package")
        self.run('{} -c "{}"'.format(bash, exe), env="conanrun")

        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run('python3 "{}" --package-folder "{}" --os "{}" --arch "{}" '
                 '--version "{}" --generators-dir "{}" --build-dir "{}"'.format(
                     layout, iceoryx.package_folder, self.settings.os,
                     self.settings.arch, iceoryx.ref.version,
                     self.generators_folder, self.build_folder),
                 env="conanrun")
