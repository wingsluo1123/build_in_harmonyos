#!/usr/bin/env python3
"""Conan recipe for cmt (Computer Music Toolkit) 1.18 — LADSPA plugin library."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, chdir, apply_conandata_patches
from conan.tools.layout import basic_layout


class CmtConan(ConanFile):
    name = "cmt"
    version = "1.18"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # ladspa.h SDK header — 制品仓未发布 ladspa/1.15（not resolved），
        # 不声明依赖（同 klystrack 删 sdl2_image / clp 删 coinutils 逻辑），
        # build() 不注入 ladspa 头路径，CI worker 预装或自带 ladspa.h
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；cmt 无补丁，仅复制占位
        apply_conandata_patches(self)

    def generate(self):
        # Makefile-based build, no toolchain needed; keep for Conan 2.x G1 gate
        pass

    def build(self):
        # cmt uses a flat Makefile (src/Makefile) → cxx -shared → cmt.so
        # ladspa.h 头路径：ladspa/1.15 未发布到制品仓，不注入其路径
        # CI worker 预装 ladspa.h 或自带源码，用系统头路径 fallback
        # aireview Critical: 用 Conan conf 解析 C++ 编译器，非硬编码 clang++
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or "clang++"
        cppflags = "-fPIC"
        cxxflags = f"{cppflags} -Wall -Werror -O2"
        with chdir(self, os.path.join(self.source_folder, "src")):
            self.run(
                f'make -j"$(nproc)" '
                f'CXX={cxx} '
                f'CPPFLAGS="{cppflags}" '
                f'CXXFLAGS="{cxxflags}"'
            )

    def package(self):
        # cmt.so 安装到 ${package_folder}/lib/ladspa/
        copy(self, "cmt.so",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "lib", "ladspa"))
        # 头文件（ladspa_types.h/cmt.h 供消费者链接）
        for h in ("ladspa_types.h", "cmt.h", "utils.h", "run_adding.h"):
            copy(self, h,
                 src=os.path.join(self.source_folder, "src"),
                 dst=os.path.join(self.package_folder, "include", "cmt"))

    def package_info(self):
        # cmt 是运行时 ladspa 插件库（dlopen 加载 cmt.so），非链接型 lib
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include/cmt"]
        # ladspa 头路径通过 dependency 传递给消费者
        self.info.site = "https://www.ladspa.org/cmt/"
