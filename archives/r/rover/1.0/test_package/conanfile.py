#!/usr/bin/env python3
"""test_package for rover 1.0 — 运行包内 bin/rover，校验产物真实可用。

交叉目标（OHOS/aarch64）在宿主上不可执行时，仅校验产物存在并给出告警，
不伪造成败；本机/模拟器可运行时会真正执行 `rover -v` 并断言输出。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class RoverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self.run("clang test.c -o test_rover")

    def test(self):
        pkg = self.dependencies["rover"].package_folder
        bin_path = os.path.join(pkg, "bin", "rover")
        if not os.path.isfile(bin_path):
            raise ConanException(f"rover binary missing: {bin_path}")
        if not can_run(self):
            self.output.warning(
                f"cross-built for {self.settings.os}/{self.settings.arch}: "
                f"skip running {bin_path} on the build host"
            )
            return
        self.run(f"./test_rover {bin_path}")
