#!/usr/bin/env python3
"""Conan recipe — brogue 1.14.1-r2 (Makefile).

Brogue is a roguelike game.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class BrogueConan(ConanFile):
    name = "brogue"
    version = "1.14.1-r2"
    description = "Roguelike game"
    license = "AGPL-3.0-or-later"
    homepage = "https://sites.google.com/site/broguegame/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # brogue 上游 term.c 用 #include <ncurses.h>，OHOS 无独立 ncurses，用 Conan 配方兼容
        # （ncurses/6.4@ohpcd/stable 提供 libncursesw.a + 头文件）
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Use terminal mode instead of SDL graphics (no SDL2 available on OHOS)
        # 上游 config.mk 在源根目录（非 src/），修正 sed 路径
        self.run(f"cd {self.source_folder} && sed -i 's/TERMINAL := NO/TERMINAL := YES/' config.mk")
        self.run(f"cd {self.source_folder} && sed -i 's/GRAPHICS := YES/GRAPHICS := NO/' config.mk")
        opt_flag = {"Debug": "-g -O0", "Release": "-O2", "RelWithDebInfo": "-O2 -g", "MinSizeRel": "-Os"}.get(str(self.settings.build_type), "-O2")
        # ncurses Conan 配方路径（依赖后 cpp_info.libdirs/includedirs 自动注入）
        ncurses_inc = os.path.join(self.dependencies["ncurses"].package_folder, "include")
        ncurses_lib = os.path.join(self.dependencies["ncurses"].package_folder, "lib")
        # 上游 Makefile 在源根目录（非 src/），修正 make 路径
        # 加 -I{ncurses_inc} 让 term.c #include <ncurses.h> 找到头文件，LDFLAGS=-L... -lncursesw 链接库
        cc = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict).get('c','cc')
        self.run(f"cd {self.source_folder} && make CC='{cc}' CFLAGS='{opt_flag} -I{ncurses_inc}' LDFLAGS='-L{ncurses_lib} -lncursesw'")
        # Run upstream regression tests
        self.run(f"cd {self.source_folder}/test && python3 run_regression_tests.py 2>&1", cwd=self.source_folder)

    def package(self):
        self.run(f"mkdir -p {self.package_folder}/bin")
        self.run(f"cp {self.source_folder}/bin/brogue {self.package_folder}/bin/")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
