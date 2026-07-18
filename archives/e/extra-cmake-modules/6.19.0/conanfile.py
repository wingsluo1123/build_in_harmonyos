#!/usr/bin/env python3
"""Conan recipe — extra-cmake-modules (ECM) 6.19.0.

ECM 是纯 CMake 模块包（无 C/C++ 编译产物），只安装 .cmake/.py 脚本到 share/ECM/。
下游 KDE Frameworks 6 库（ki18n/karchive/kdoctools 等）通过 find_package(ECM) 引用。

构建系统：CMake（cmake-only，无 compiler）
平台：OHOS / Linux / macOS / Windows
依赖：零运行时依赖（构建时可选 Sphinx/Qt5/Qt6/Python3 仅用于文档/测试）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.cmake import CMake, cmake_layout


class ExtraCMakeModulesConan(ConanFile):
    name = "extra-cmake-modules"
    version = "6.19.0"
    description = "Extra CMake Modules — KDE 社区扩展 CMake 模块包，提供 find_package/find_modules/common build settings"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/frameworks/extra-cmake-modules"
    url = ""  # CI fills this

    # R32: settings.os 判断必须 in ("Linux", "OHOS")，但 ECM 无编译产物，
    # settings 仅用于 conan create 验证可移植性
    settings = "os", "compiler", "build_type", "arch"

    # 无编译产物 → 不声明 cpp_info.libs（R26 系统同名库隔离不适用）
    # 无运行时依赖 → requirements() 为空

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # ECM 无运行时依赖

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # ECM 是 cmake-only 模块包：configure 只用于生成 ECMConfig.cmake，
        # build 只编译少量测试静态库（用于 ECMGeneratePkgConfigFile 自测），不影响产物
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # ECM 产物是 share/ECM/ 下的 .cmake/.py/.in 脚本，无 bin/lib/include
        copy(self, "*", os.path.join(self.source_folder, "build"),
             os.path.join(self.package_folder, "share/ECM"), excludes=["*.log", "CMakeCache.txt"])
        # 直接从源码树拷贝（cmake install 的标准产物布局）
        copy(self, "*.cmake", os.path.join(self.source_folder, "modules"),
             os.path.join(self.package_folder, "share/ECM/modules"))
        copy(self, "*.cmake", os.path.join(self.source_folder, "kde-modules"),
             os.path.join(self.package_folder, "share/ECM/kde-modules"))
        copy(self, "*.cmake", os.path.join(self.source_folder, "find-modules"),
             os.path.join(self.package_folder, "share/ECM/find-modules"))
        copy(self, "*.cmake", os.path.join(self.source_folder, "toolchain"),
             os.path.join(self.package_folder, "share/ECM/toolchain"))
        copy(self, "*", os.path.join(self.source_folder, "cmake"),
             os.path.join(self.package_folder, "share/ECM/cmake"))
        # ECMConfig.cmake.in 需替换为实际安装路径——CI build() 内 cmake.configure 会处理
        copy(self, "ECMConfig.cmake", os.path.join(self.source_folder, "build"),
             os.path.join(self.package_folder, "share/ECM/cmake"))

    def package_info(self):
        # ECM 是 CMake 模块包，下游通过 find_package(ECM) 引用，
        # 不通过 cpp_info.libs / cpp_info.includedirs 链接
        # 告知下游 ECM 的 cmake 模块路径
        ecm_share = os.path.join(self.package_folder, "share", "ECM")
        self.cpp_info.set_property("cmake_file", os.path.join(ecm_share, "cmake", "ECMConfig.cmake"))
        self.cpp_info.set_property("cmake_target_name", "ECM")
        # 关键：让 find_package(ECM) 能找到模块目录
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "cmake"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "modules"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "kde-modules"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "find-modules"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "toolchain"))
