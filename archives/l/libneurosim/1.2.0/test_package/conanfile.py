#!/usr/bin/env python3
"""Conan consumer test for libneurosim 1.2.0 — 版本查询 + 连接生成 API 冒烟。"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["libneurosim"].package_folder
        cc = os.environ.get("CXX", "clang++")
        src = os.path.join(self.source_folder, "test_neurosim.cc")
        self.run(
            f"{cc} -std=c++11 -o test_neurosim {src} "
            f"-I{pkg}/include -L{pkg}/lib -lneurosim -lm",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_neurosim", env="conanrun")
