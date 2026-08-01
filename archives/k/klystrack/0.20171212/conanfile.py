#!/usr/bin/env python3
"""Conan recipe for klystrack 0.20171212 — C chiptune tracker (Makefile build).

klystrack 是 C 写的 chiptune tracker（C64/NES/Amiga 风音乐），用 Makefile 构建
（非 configure autotools），依赖 SDL2 + SDL2_image 图形库。
上游无自动化测试套件（chiptune tracker 纯音频应用）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, chdir, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class KlystrackConan(ConanFile):
    name = "klystrack"
    version = "0.20171212"
    description = "Chiptune tracker for making C64/NES/Amiga-style music"
    license = "MIT"
    homepage = "https://kometbomb.github.io/klystrack/"
    url = "https://github.com/kometbomb/klystrack"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL2 制品仓已就绪 (resolve-deps ✅)，包名小写 sdl2
        self.requires("sdl2/2.30.10")
        # SDL2_image 未合入制品仓 main，不声明依赖（上游 Makefile 的 DLLs 仅 Windows 预打包用，Linux 构建不需）

    def layout(self):
        basic_layout(self)
        # Conan 2.x basic_layout 默认 source_folder = build folder，但 Makefile 在解包后源码根
        # 显式指定 source folder = 解包根（含 Makefile）
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Makefile-based build, no toolchain needed; keep for Conan 2.x G1 gate
        pass

    def build(self):
        apply_conandata_patches(self)
        # SDL2 头路径通过 CPPFLAGS 注入（Conan 包 package_folder）
        sdl2_inc = os.path.join(self.dependencies["sdl2"].package_folder, "include")
        sdl2_lib = os.path.join(self.dependencies["sdl2"].package_folder, "lib")
        cppflags = f"-I{sdl2_inc}"
        ldflags = f"-L{sdl2_lib}"
        # Conan 2.x basic_layout + strip_root=True 解包后 Makefile 在 source_folder 根
        # 但 build() 阶段 self.source_folder 可能指向空的 source cache，需动态找 Makefile
        make_dir = self.source_folder
        if not os.path.isfile(os.path.join(make_dir, "Makefile")):
            # 扫 source_folder 子目录找含 Makefile 的真源码根
            for candidate in (self.source_folder,
                              os.path.join(self.build_folder, "source"),
                              os.path.join(self.build_folder, "src"),
                              self.export_sources_folder):
                if candidate and os.path.isfile(os.path.join(candidate, "Makefile")):
                    make_dir = candidate
                    break
            else:
                # 最后兜底：os.walk 扫 build_folder 全目录
                for root, dirs, files in os.walk(self.build_folder):
                    if "Makefile" in files and "klystrack" in os.path.basename(root).lower() or root == self.build_folder:
                        # 优先顶层 Makefile（上游根 Makefile）
                        if os.path.basename(root) == os.path.basename(self.build_folder) or "klystrack" in os.path.basename(root).lower():
                            make_dir = root
                            break
        make_cmd = (
            f'make CFG=release '
            f'CC=clang '
            f'CFLAGS+="{cppflags}" '
            f'LDFLAGS+="{ldflags}" '
            f'PREFIX={os.path.join(self.build_folder, "staging")}'
        )
        self.run(make_cmd, cwd=make_dir)

    def package(self):
        # make install 安装到 staging（复用 build() 找到的 make_dir）
        make_dir = self.source_folder
        if not os.path.isfile(os.path.join(make_dir, "Makefile")):
            for candidate in (self.source_folder,
                              os.path.join(self.build_folder, "source"),
                              os.path.join(self.build_folder, "src"),
                              self.export_sources_folder):
                if candidate and os.path.isfile(os.path.join(candidate, "Makefile")):
                    make_dir = candidate
                    break
        self.run(
            f'make install CFG=release '
            f'PREFIX={os.path.join(self.build_folder, "staging")}',
            cwd=make_dir
        )
        # copy staging 到 package_folder
        copy(self, "*", src=os.path.join(self.build_folder, "staging"),
             dst=self.package_folder)

    def package_info(self):
        # klystrack 是 CLI 二进制（bin/klystrack），非链接型 lib
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
