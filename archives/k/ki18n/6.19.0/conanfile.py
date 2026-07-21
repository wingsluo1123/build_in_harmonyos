#!/usr/bin/env python3
"""Conan recipe — ki18n 6.19.0 (KDE Frameworks 6).

ki18n 是 KDE 国际化框架，提供 KLocalizedString 系列 API。
构建系统：CMake（find_package(ECM 6.19 REQUIRED) + Qt6 + gettext）
依赖：ECM 6.19.0 + Qt6 qtbase + gettext + libintl

R36: 依赖按拓扑序先发布（ECM + qtbase 就位后本配方 CI 验证）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, cmake_layout


class KI18nConan(ConanFile):
    name = "ki18n"
    version = "6.19.0"
    description = "KDE 国际化框架，提供 KLocalizedString 系列翻译 API"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/frameworks/ki18n"
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
        self.requires("qtbase/[>=6.5 <7]")  # Qt6 待赛事发布
        # gettext 系统库由 R26 静态隔离处理

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
        # R-CI8 同范式：精确复制避 R19 包污染
        copy(self, "*.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include/KF6/KI18n"))
        copy(self, "*.so", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", os.path.join(self.build_folder, "lib"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        # cmake config files
        copy(self, "KF6I18nConfig*.cmake", os.path.join(self.build_folder),
             os.path.join(self.package_folder, "lib/cmake/KF6I18n"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["KF6I18n"]
        self.cpp_info.set_property("cmake_file", "lib/cmake/KF6I18n/KF6I18nConfig.cmake")
        self.cpp_info.set_property("cmake_target_name", "KF6::I18n")
