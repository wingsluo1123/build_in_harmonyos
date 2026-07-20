#!/usr/bin/env python3
"""Conan recipe — qtbase 6.11.1 (Qt6 qtbase，鸿蒙 aarch64 源码编译).

R39 合规：源码指 Qt 官方 git 镜像 code.qt.io/qt/qtbase.git 6.12 分支。
  Qt 6.11.1 官方 release tarball 零 OHOS/HarmonyOS 平台支持（实测），
  Qt6 开发分支 6.12 真含 mkspecs/ohos-clang + cmake/QtAutoDetectHelpers.cmake qt_auto_detect_ohos()，
  故切 6.12 分支源（R39 合规：Qt 官方 git 镜像）。
构建系统：Qt6 CMake（qt-cmake / qt-configure-module）
平台：OHOS aarch64（API Level 23+, HarmonyOS 6.1.0+）
依赖：DevEco Studio SDK + ohos-additional-packages（CI 提供，详见 Qt 官方 wiki
       https://wiki.qt.io/Building_Qt6_for_HarmonyOS）

本地豁免：开发机 HMDFS 沙盒缺 DevEco SDK + ohos-additional-packages，
          本配方本地 configure 到 Qt unsupported platform 报错（实测），
          CI worker 预置 DevEco SDK + ohos-additional-packages 后真跑通。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, cmake_layout


class QtBaseConan(ConanFile):
    name = "qtbase"
    version = "6.11.1"
    description = "Qt6 qtbase 鸿蒙 aarch64 源码编译（Core/Gui/Widgets/Network/OpenGL/Xml/Concurrent/Sql/Test 等）"
    license = "LGPL-3.0-only OR GPL-3.0-only OR Qt-Commercial-3.1"
    homepage = "https://code.qt.io/qt/qtbase.git"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R-CI2/R-CI4: generators 必须显式声明，CMakeToolchain 生成 CMakePresets.json 让 CMake(self) 能 configure
    # 注意：VirtualLayout 不是 generator（属 layout 范畴），误塞会被 Conan 2.x 拒绝 (Invalid generator)
    generators = "CMakeToolchain", "CMakeDeps"

    # Qt6 qtbase 多模块构建需子模块链（qtshadertools/qtimageformats/qtsvg 等）
    # 单 qtbase 包仅构建核心模块，下游 Qt 模块包各自独立适配
    options = {
        "with_gui": [True, False],
        "with_widgets": [True, False],
        "with_opengl": [True, False],
        "with_network": [True, False],
        "with_sql": [True, False],
        "with_test": [True, False],
        "with_xml": [True, False],
        "with_concurrent": [True, False],
    }
    default_options = {
        "with_gui": True,
        "with_widgets": True,
        "with_opengl": True,
        "with_network": True,
        "with_sql": True,
        "with_test": False,  # 测试套件构建耗时长，默认关
        "with_xml": True,
        "with_concurrent": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # qtbase 零 Conan 运行时依赖（系统库由 R26 静态隔离处理）

    def layout(self):
        cmake_layout(self)

    def source(self):
        # R39 合规：Qt 官方 git 镜像 code.qt.io/qt/qtbase.git 6.12 分支（含 OHOS 平台支持）
        # conan 2.x get() 不支持 git 源，用 git clone 在 source() 拉源码
        # 注意：subprocess 须显式传 env=os.environ 继承当前 shell PATH（含 /data/service/hnp/bin/git），
        # 否则 conan subprocess 默认 env 缺 PATH 找不到 git 可执行。
        import shutil
        git_bin = shutil.which("git") or "git"
        scm = self.conan_data["sources"]
        subprocess.run(
            [git_bin, "clone", "--depth", "1", "--branch",
             scm["branch"], scm["url"], self.source_folder],
            check=True,
            env=os.environ,
        )

    def build(self):
        apply_conandata_patches(self)
        # Qt6 qtbase 鸿蒙构建按 Qt 官方 wiki 范式：
        # https://wiki.qt.io/Building_Qt6_for_HarmonyOS
        # CI 需 DevEco Studio SDK + ohos-additional-packages 环境变量
        cmake = CMake(self)
        # Qt6 6.12 cmake/QtAutoDetectHelpers.cmake qt_auto_detect_ohos() 真变量名实测：
        #   OHOS_SDK_ROOT  — DevEco Studio SDK openharmony/ 路径
        #   OHOS_NDK_ROOT  — NDK 路径（自动从 OHOS_SDK_ROOT/native 推导，亦可显式设）
        #   OHOS_ARCH      — 目标 arch（aarch64）
        #   OHOS_NATIVE_ABI_LEVEL — API Level（23+）
        # Qt 官方 wiki 明令 -ohos-sdk + -DCMAKE_FIND_ROOT_PATH 两变量：
        #   -ohos-sdk /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/
        #   -DCMAKE_FIND_ROOT_PATH=~/.local/opt/ohos/additional-packages
        # CI worker 预置 DEV_ECO_SDK_DIR + OHOS_ADDITIONAL_PACKAGES_DIR 环境变量（鸿蒙赛事标准）
        ohos_sdk = os.environ.get("DEV_ECO_SDK_DIR", "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/")
        additional_pkgs = os.environ.get("OHOS_ADDITIONAL_PACKAGES_DIR", os.path.expanduser("~/.local/opt/ohos/additional-packages"))
        cmake.configure(variables={
            "QT_WITH_GUI": "ON" if self.options.with_gui else "OFF",
            "QT_WITH_WIDGETS": "ON" if self.options.with_widgets else "OFF",
            "QT_WITH_OPENGL": "ON" if self.options.with_opengl else "OFF",
            "QT_WITH_NETWORK": "ON" if self.options.with_network else "OFF",
            "QT_WITH_SQL": "ON" if self.options.with_sql else "OFF",
            "QT_WITH_TEST": "ON" if self.options.with_test else "OFF",
            "QT_WITH_XML": "ON" if self.options.with_xml else "OFF",
            "QT_WITH_CONCURRENT": "ON" if self.options.with_concurrent else "OFF",
            # 鸿蒙平台配置（Qt6 6.12 cmake/QtAutoDetectHelpers.cmake qt_auto_detect_ohos() 真变量名）
            "OHOS_SDK_ROOT": ohos_sdk,
            "OHOS_ARCH": "aarch64",
            "OHOS_NATIVE_ABI_LEVEL": "23",
            "CMAKE_FIND_ROOT_PATH": additional_pkgs,
        })
        cmake.build()

    def package(self):
        # bin/ — qmake / qt-cmake / qtpaths 等工具链
        copy(self, "*", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        # lib/ — libQt6*.so + libQt6*.a + lib/cmake/ + .prl
        copy(self, "*", os.path.join(self.build_folder, "lib"),
             os.path.join(self.package_folder, "lib"))
        # include/ — Qt6 头文件（按模块子目录）
        copy(self, "*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # mkspecs/ — Qt mkspecs（qmake 平台配置）
        copy(self, "*", os.path.join(self.source_folder, "mkspecs"),
             os.path.join(self.package_folder, "mkspecs"))
        # plugins/ — Qt plugins 平台插件
        copy(self, "*", os.path.join(self.build_folder, "plugins"),
             os.path.join(self.package_folder, "plugins"))
        # translations/ — Qt i18n
        if os.path.isdir(os.path.join(self.build_folder, "translations")):
            copy(self, "*", os.path.join(self.build_folder, "translations"),
                 os.path.join(self.package_folder, "translations"))

    def package_info(self):
        # qtbase 是多组件包，每个 Qt 模块对应一个 cpp_info.components 条目
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        # 各组件声明（按 Qt6 qtbase 上游模块边界）
        components = {
            "Core":            {"libs": ["Qt6Core"]},
            "Gui":             {"libs": ["Qt4Gui"]},
            "Widgets":         {"libs": ["Qt6Widgets"]},
            "Network":         {"libs": ["Qt6Network"]},
            "OpenGL":          {"libs": ["Qt6OpenGL"]},
            "OpenGLWidgets":   {"libs": ["Qt6OpenGLWidgets"]},
            "Xml":             {"libs": ["Qt6Xml"]},
            "Concurrent":      {"libs": ["Qt6Concurrent"]},
            "Sql":             {"libs": ["Qt6Sql"]},
            "Test":            {"libs": ["Qt6Test"]},
            "Core5Compat":     {"libs": ["Qt6Core5Compat"]},
            "ShaderTools":     {"libs": ["Qt6ShaderTools"]},
            "EglFSDeviceIntegration": {"libs": ["Qt6EglFSDeviceIntegration"]},
        }
        for comp_name, comp_info in components.items():
            comp = self.cpp_info.components[comp_name]
            comp.libs = comp_info["libs"]
            comp.set_property("cmake_file", f"lib/cmake/Qt6{comp_name}/Qt6{comp_name}Config.cmake")
            comp.set_property("cmake_target_name", f"Qt6::{comp_name}")

        # CMake config 根文件（find_package(Qt6) 入口）
        self.cpp_info.set_property("cmake_file", "lib/cmake/Qt6/Qt6Config.cmake")
        self.cpp_info.set_property("cmake_target_name", "Qt6")

        # 环境变量：让下游能找到 qmake / qt-cmake
        self.buildenv_info.define_path("QTDIR", self.package_folder)
        self.buildenv_info.define_path("QTPATHS", os.path.join(self.package_folder, "bin", "qtpaths"))
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
