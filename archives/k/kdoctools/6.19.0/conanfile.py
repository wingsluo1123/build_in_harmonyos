#!/usr/bin/env python3
"""Conan recipe — kdoctools 6.19.0（KDE DocBook 文档处理工具）.

kdoctools 提供 meinproc/meinproc5 等工具，将 DocBook XML 文档转换为
HTML/Man/Info 等格式，供 KDE 帮助系统使用。
构建系统：CMake
平台：OHOS aarch64 / Linux / macOS
依赖：ECM、Qt6Core（qtbase）、libxml2、libxslt
已知限制：KF6Archive 未合入（karchive 无 Conan 配方），采用 KDE 官方
MEINPROC_NO_KARCHIVE 降级（meinproc cache 选项不可用，DocBook 转换正常）；
KF6I18n 为 OPTIONAL（翻译功能，跳过）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KDocToolsConan(ConanFile):
    name = "kdoctools"
    version = "6.19.0"
    description = "kdoctools — KDE DocBook documentation processing tools"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdoctools"
    url = "https://invent.kde.org/frameworks/kdoctools"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("extra-cmake-modules/6.19.0")
        self.requires("qtbase/6.11.1")
        # libxml2 用 2.15.3：与 libxslt/1.1.45.1 的依赖版本一致，避免版本冲突
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # qtbase 预构建产物无 Qt6Config.cmake（cmake_find_mode=none），
        # ECM 的 ECMQueryQt.cmake 依赖 Qt6::qtpaths target 查询 Qt 安装前缀，
        # 缺失即 FATAL_ERROR。生成 qtpaths_target.cmake 并通过 conf
        # tools.cmake.cmaketoolchain:user_toolchain 注入（CMakeToolchain 生成时读取）。
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        qtpaths = os.path.join(qtbase_pkg, "bin", "qtpaths")
        toolchain_file = os.path.join(self.generators_folder, "qtpaths_target.cmake")
        with open(toolchain_file, "w") as f:
            f.write("if(NOT TARGET Qt6::qtpaths)\n")
            f.write(f"    add_executable(Qt6::qtpaths IMPORTED)\n")
            f.write(f"    set_target_properties(Qt6::qtpaths PROPERTIES IMPORTED_LOCATION \"{qtpaths}\")\n")
            f.write("endif()\n")
        self.conf.define("tools.cmake.cmaketoolchain:user_toolchain", [toolchain_file])

        tc = CMakeToolchain(self)
        # karchive 未合入且无 Conan 配方，采用 KDE 官方 MEINPROC_NO_KARCHIVE
        # 降级（meinproc cache 选项不可用，DocBook 转换核心功能正常）
        tc.variables["MEINPROC_NO_KARCHIVE"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "KF6DocTools")
        self.cpp_info.set_property("cmake_target_name", "KF6::DocTools")