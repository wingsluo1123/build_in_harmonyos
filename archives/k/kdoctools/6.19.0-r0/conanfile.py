#!/usr/bin/env python3
"""Conan recipe — kdoctools 6.19.0 (KDE Frameworks 6, Alpine revision r0).

kdoctools 是 KDE 文档工具集，提供 mecut/transform/man 链式文档构建工具。
构建系统：CMake（find_package(ECM 6.19 REQUIRED) + Qt6 + ki18n + karchive + libxml2/libxslt）
依赖：ECM 6.19.0 + Qt6 qtbase + ki18n 6.19.0 + karchive 6.19.0 + libxml2/libxslt（系统库）

R36: 依赖按拓扑序先发布（ECM + qtbase + ki18n + karchive 就位后本配方 CI 验证）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, cmake_layout


class KDocToolsConan(ConanFile):
    name = "kdoctools"
    version = "6.19.0-r0"  # Alpine revision r0，上游 KDE Frameworks 6.19.0
    description = "KDE 文档工具集，提供 mecut/transform/man 链式文档构建工具"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/frameworks/kdoctools"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # 与 ECM R-CI2/R-CI4 同范式：generators 显式声明，CMakeToolchain 生成 CMakePresets.json 让 CMake(self) 能 configure
    # 注意：VirtualLayout 不是 generator（属 layout 范畴），误塞会被 Conan 2.x 拒绝 (Invalid generator)
    generators = "CMakeToolchain", "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36: 依赖必须按拓扑序先发布
        self.requires("extra-cmake-modules/6.19.0")
        self.requires("ki18n/6.19.0")
        self.requires("karchive/6.19.0")
        self.requires("qtbase/[>=6.5 <7]")  # Qt6 待赛事发布
        # 系统库 libxml2/libxslt/docbook-xml 由 R26 静态隔离处理（暂略）

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "*.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include/KF6/KDocTools"))
        copy(self, "*", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "*.so", os.path.join(self.build_folder, "lib"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "KF6DocToolsConfig*.cmake", os.path.join(self.build_folder),
             os.path.join(self.package_folder, "lib/cmake/KF6DocTools"), keep_path=False)
        # 宏定义文件（me5/man 链式构建所需）
        copy(self, "KF6DocToolsMacros.cmake", os.path.join(self.source_folder),
             os.path.join(self.package_folder, "share/ECM/kde-modules"))

    def package_info(self):
        self.cpp_info.libs = ["KF6DocTools"]
        self.cpp_info.set_property("cmake_file", "lib/cmake/KF6DocTools/KF6DocToolsConfig.cmake")
        self.cpp_info.set_property("cmake_target_name", "KF6::DocTools")
