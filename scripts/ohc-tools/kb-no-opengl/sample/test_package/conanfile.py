import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conanfile import inject_qt6_cmakdirs  # noqa: E402


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt6 的 config 文件由 qtbase 包提供（cmake_find_mode=none，需显式注入 _DIR）
        inject_qt6_cmakdirs(self, tc)
        # 被测包：不用 CMakeDeps 的 config（它对 qtbase 会生成 find_dependency(qtbase)，
        # 而 qtbase 不提供 <name>-config.cmake），直接给出已安装产物路径。
        tested = self.dependencies[self.tested_reference_str]
        tc.variables["NOOPENGLDEMO_INCLUDE_DIR"] = os.path.join(
            tested.package_folder, "include"
        )
        tc.variables["NOOPENGLDEMO_LIB_DIR"] = os.path.join(
            tested.package_folder, "lib"
        )
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindirs[0], "noopengl_demo_test")
            self.run(exe, env="conanrun")
