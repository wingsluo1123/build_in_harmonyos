#!/usr/bin/env python3
"""Conan consumer test for sofia 1.13.17 — su 层 API 冒烟（SIP 协议栈核心）。"""

import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["sofia"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_sofia.c")
        self.run(
            f"{cc} -o test_sofia {src} "
            f"-I{pkg}/include/sofia-sip-1.13 -L{pkg}/lib -lsofia-sip-ua -lm -lpthread -ldl",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        self.run("./test_sofia", env="conanrun")
