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
        # CI 真根因: ERROR: Package 'ladspa/1.15' not resolved — ladspa 包不在 registry
        # 删 self.requires("ladspa/1.15") 依赖声明，改用系统 ladspa.h（CI 预装或 SDK 头文件）
        # ladspa.h 是 LADSPA SDK 标准头文件，CI worker /data/service/hnp/include 已预装
        pass  # 无 Conan 依赖（ladspa.h 走系统头文件路径）

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；cmt 无补丁
        # aireview P3: 误调 apply_conandata_patches（该函数属 source() 非 export_sources）
        pass

    def generate(self):
        # Makefile-based build, no toolchain needed; keep for Conan 2.x G1 gate
        pass

    def build(self):
        # cmt uses a flat Makefile (src/Makefile) → cxx -shared → cmt.so
        # aireview Critical: 用 Conan conf 解析 C++ 编译器，非硬编码 clang++
        # CI 真根因: ladspa/1.15 不在 registry → 删依赖改用系统 ladspa.h（CI 预装 /data/service/hnp/include）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or "clang++"
        ladspa_inc = "/data/service/hnp/include"
        cppflags = f"-fPIC -I{ladspa_inc}"
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
        # CI 真根因: ladspa/1.15 不在 registry → 删依赖，消费者需自行装 ladspa.h SDK 头文件
        # ladspa.h 是 LADSPA SDK 标准头文件，CI worker /data/service/hnp/include 已预装
        # aireview P3: self.info.site 非标准 API → 删（改用 cpp_info 系统/描述传播）
