import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class TguiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Ninja on OHOS for the same reason as the package build (E346): the
        # sandbox denies make's hardcoded SHELL=/bin/sh, which breaks CMake's
        # configure-stage try_compile.
        generator = "Ninja" if str(self.settings.os) == "OHOS" else None
        tc = CMakeToolchain(self, generator=generator)
        if generator == "Ninja":
            ninja = "/data/service/hnp/bin/ninja"
            tc.variables["CMAKE_MAKE_PROGRAM"] = (
                ninja if os.path.isfile(ninja) else (shutil.which("ninja") or "ninja")
            )
        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindir, "test_tgui")
            self.run(f'"{test_bin}"', env="conanrun")
