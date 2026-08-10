#!/usr/bin/env python3
"""Conan recipe — fizmo 0.8.5（Z-Machine 交互小说解释器）.

fizmo 是 Z-Machine 解释器（Fizmo Interprets Z-Machine Opcodes），
可运行 Infocom 及大部分 Z-Machine 交互小说（版本 1-5, 7, 8）。
构建系统：GNU Autotools（configure + make）
平台：OHOS aarch64 / Linux / macOS
依赖：ncurses/6.5（fizmo-ncursesw 前端需要 wide-char ncursesw）
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools


class FizmoConan(ConanFile):
    name = "fizmo"
    version = "0.8.5"
    description = "fizmo — Z-Machine interpreter (Z-Machine interactive fiction)"
    license = "BSD-3-Clause"
    homepage = "https://fizmo.spellbreaker.org/"
    url = "https://github.com/chrender/fizmo"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # fizmo-ncursesw 前端依赖 wide-char ncurses（ncursesw）
        self.requires("ncurses/6.5")
        # fizmo configure 检测 libxml-2.0（pkg-config）+ libxml/tree.h，缺依赖
        # 则报 "Could not find libxml/tree.h"（CI #17356）
        self.requires("libxml2/2.15.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _machine(self, arch):
        # 从 arch setting 推导 GNU 三元组 machine 部分
        return {
            "armv8": "aarch64",
            "armv7": "arm",
            "x86_64": "x86_64",
            "x86": "i686",
        }.get(str(arch), str(arch))

    def generate(self):
        tc = AutotoolsToolchain(self)
        # fizmo 的 config.guess 可能无法识别 HarmonyOS，指定 --build/--host 三元组
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        tc.configure_args.extend([f"--build={triplet}", f"--host={triplet}"])
        # fizmo configure 硬编码路径检测 libxml/tree.h（/usr/include/libxml2 等），
        # 需传 --with-libxml2-includedir 指向 libxml2 包 include
        tc.configure_args.append(
            "--with-libxml2-includedir="
            f"{os.path.join(self.dependencies['libxml2'].package_folder, 'include', 'libxml2')}")
        tc.generate()
        # libxml2 的 pkg-config（libxml-2.0）加入 PKG_CONFIG_PATH
        from conan.tools.env import Environment
        env = Environment()
        env.append_path(
            "PKG_CONFIG_PATH",
            os.path.join(self.dependencies["libxml2"].package_folder, "lib", "pkgconfig"),
        )
        env.vars(self).save_script("conanbuild_pkgconfig")

    def build(self):
        autotools = Autotools(self)
        # OHOS 沙箱 umask 077 导致 config.status 临时目录不可写，临时改 022
        old_umask = os.umask(0o022)
        try:
            autotools.configure()
            # -j1 避免 mkfifo 沙箱限制（opensp 先例）
            autotools.make(args=["-j1"])
        finally:
            os.umask(old_umask)

    def package(self):
        # fizmo-ncursesw 前端二进制在源码构建产物中，复制到 bin/
        from conan.tools.files import copy
        copy(self, "fizmo-ncursesw", os.path.join(self.build_folder, "fizmo-ncursesw"),
             os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []