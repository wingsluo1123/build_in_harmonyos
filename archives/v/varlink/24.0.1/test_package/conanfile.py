#!/usr/bin/env python3
"""Conan consumer test for varlink 24.0.1 — libvarlink 对象 API 冒烟。"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["varlink"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_varlink.c")
        self.run(
            f"{cc} -o test_varlink {src} "
            f"-I{pkg}/include -L{pkg}/lib -lvarlink -lm -lpthread",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        # conanrun 未把依赖包 libdir 注入 LD_LIBRARY_PATH（OHOS loader 找不到
        # libvarlink.so.0），显式注入后运行测试二进制
        libdir = os.path.join(self.dependencies["varlink"].package_folder, "lib")
        self.run(f"LD_LIBRARY_PATH='{libdir}' ./test_varlink", env="conanrun")
