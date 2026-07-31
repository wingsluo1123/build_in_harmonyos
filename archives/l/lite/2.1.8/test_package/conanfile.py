#!/usr/bin/env python3
"""Conan test_package for lite 2.1.8 (lite-xl).

Builds test_litexl with MesonToolchain, then runs it against the installed
lite-xl binary.  R34: the test GENUINELY executes the packaged lite-xl binary
with a real embedded-Lua command and asserts on its runtime output — not a
print-only shell test (see test_litexl.c).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LiteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        dep = self.dependencies["lite"]
        bindir = dep.cpp_info.bindirs[0]
        litexl = os.path.join(dep.package_folder, bindir, "lite-xl")
        # OHOS 上 /system/bin/sh (mksh) 不能直接 exec ELF，用 bash 包一层执行
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 真实调用被测二进制；env=conanrun 提供全部依赖库路径（LD_LIBRARY_PATH），
        # 保证 lite-xl 运行期能找到 freetype 等 conan 依赖的 .so。
        self.run(
            f'LITE_XL_BIN="{litexl}" {bash} -c "./test_litexl"',
            env="conanrun",
        )
