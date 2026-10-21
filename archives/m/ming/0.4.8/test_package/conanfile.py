#!/usr/bin/env python3
"""Conan consumer test for ming 0.4.8 — libming SWF 库 API 冒烟。"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libming.a 链接需 zlib（compress2），zlib 为传递依赖——直接 require 以便取路径
        self.requires("zlib/1.3.1")

    def build(self):
        pkg = self.dependencies["ming"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_ming.c")
        # libming.a 使用 zlib 的 compress2，需链接 zlib（含传递依赖路径）
        zl = self.dependencies["zlib"].package_folder
        self.run(
            f"{cc} -o test_ming {src} "
            f"-I{pkg}/include -L{pkg}/lib -L{zl}/lib "
            f"-lming -lz -lm -lpthread -ldl -Wl,-z,muldefs",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_ming", env="conanrun")
