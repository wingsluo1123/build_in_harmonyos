#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""osmin 1.15.1 —— HarmonyOS PC (OpenHarmony aarch64) Conan 配方。

上游: https://github.com/janbar/osmin   (GPL-3.0-or-later)
构建: CMake >= 3.20 + C++20 + Qt6 (Quick/QuickControls2/Widgets/Svg/Multimedia/
      RemoteObjects/Positioning/Sensors/Core5Compat，以及 dbus-1 可用时的 DBus)

libosmscout 的处理（子模块 vendor）
-----------------------------------
osmin 以 git submodule 引入 libosmscout（固定 commit acb1e4b6，osmin-1.15 分
支），backend/CMakeLists.txt 用 add_subdirectory 树内编译 OSMScout/Map/MapQt/
ClientQt/GPX 五个库，并在 configure 阶段用 `git apply` 施加
backend/libosmscout_4.patch（client-qt 画布改造）。

该子模块无法用 conan 依赖表达：制品仓的 libosmscout/2024.06.02.1 是 Framstag
上游版本、不含本补丁所需的上下文；且 conan 包无法“落到源码的子目录”。
因此本配方按上游语义在 source() 中把固定 commit 的源码放进
backend/libosmscout/，补丁依旧由上游构建逻辑施加（其逻辑对重复施打自愈：
先 --check，失败则 --reverse 回退后再 apply）。该 commit 在官方仓库
Framstag/libosmscout 与 osmin 声明的 fork janbar/libosmscout 中 tarball
字节一致（sha256 已核验相同），故 URL 取官方上游。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"

# 需要暴露 <Component>_DIR 的 Qt6 conan 包：这些包 cmake_find_mode=none，
# 组件解析由 Qt 自带的 Qt6Config.cmake + <Component>_DIR 完成。
_QT6_PACKAGES = (
    "qtbase",
    "qtdeclarative",
    "qtsvg",
    "qtmultimedia",
    "qtremoteobjects",
    "qtpositioning",
    "qtcore5compat",
    "qtsensors",
)


class OsminConan(ConanFile):
    name = "osmin"
    version = "1.15.1"
    description = (
        "GPS navigation software with OpenStreetMap vector maps, "
        "built on Qt6 Quick and libosmscout"
    )
    license = "GPL-3.0-or-later"
    url = "https://github.com/janbar/osmin"
    homepage = "https://github.com/janbar/osmin"
    topics = ("gps", "navigation", "openstreetmap", "maps", "qt6")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Qt6 组件取自 osmin CMakeLists.txt:110-112 的
        # find_package(Qt6 ... REQUIRED COMPONENTS Core Gui Qml Quick
        # QuickControls2 Widgets Xml Svg Network Sensors Multimedia
        # RemoteObjects Positioning Core5Compat)。
        # qtbase 用生态基准版本（无后缀 6.11.1）：仓内所有 Qt6 模块配方
        # （qtdeclarative/qtsvg/qtmultimedia/qtremoteobjects/qtpositioning/
        # qtcore5compat）都 requires("qtbase/6.11.1")，其已发布二进制即对着该
        # 版本构建；改成任一修复号（实测 6.11.1.3）会翻掉这些模块的 package_id，
        # 制品仓里一个模块二进制都命中不到，只能源码重建（数小时，不可行）。
        # 代价：qtbase/6.11.1 内 FEATURE_dbus=OFF，Qt::DBus 不提供，osmin 的
        # DBus 桌面集成按上游自身的 find_library(dbus-1) 守卫自动关闭。
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)
        # 直接依赖的其余 Qt6 模块：版本与生态内模块自身的要求对齐，避免"同上游
        # 版本、不同适配号"的依赖图冲突（qtdeclarative/qtsvg 用无后缀版本即此因）。
        self.requires("qtdeclarative/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtsvg/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtmultimedia/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtremoteobjects/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtpositioning/6.11.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtcore5compat/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtsensors/6.11.1", transitive_headers=True, transitive_libs=True)
        # zlib 必须是常规 requires。override 写法只改版本、不把包带进依赖图：
        # `conan graph info` 里根本没有 zlib 节点，上游 backend/CMakeLists.txt
        # 的 find_package(ZLIB QUIET) 因此必然落空，转去 download_project 内置
        # zlib-1.3.1.tar.gz。改成常规 requires 实测无版本冲突，且 qtbase 的
        # package_id 保持 01d92cf3…（可下载），`conan install --build=never`
        # rc=0——依赖解析未被翻动，制品仓二进制照常命中。
        self.requires("zlib/1.3.2")
        self.requires("libxml2/2.15.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} 目前仅适配 OHOS（Linux 语义同源）"
            )

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # 上游 git submodule: libosmscout（固定 commit）→ backend/libosmscout/
        sub = self.conan_data["libosmscout"]
        sub_dir = os.path.join(self.source_folder, "backend", "libosmscout")
        os.makedirs(sub_dir, exist_ok=True)
        get(
            self,
            url=sub["url"],
            sha256=sub["sha256"],
            destination=sub_dir,
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt6 conan 包是 cmake_find_mode=none，find_package(Qt6 COMPONENTS ...)
        # 由 Qt 自带配置逐组件解析（<Component>_DIR）；CMAKE_PREFIX_PATH 聚合
        # 对 Qt6 的逐组件查找不可靠，故显式暴露每个组件配置目录。
        for dep_name in _QT6_PACKAGES:
            try:
                pkg = self.dependencies[dep_name].package_folder
            except KeyError:
                continue
            if not pkg:
                continue
            cmake_dir = os.path.join(pkg, "lib", "cmake")
            if not os.path.isdir(cmake_dir):
                continue
            for entry in sorted(os.listdir(cmake_dir)):
                cfg_dir = os.path.join(cmake_dir, entry)
                if os.path.isdir(cfg_dir) and os.path.isfile(
                    os.path.join(cfg_dir, f"{entry}Config.cmake")
                ):
                    tc.variables[f"{entry}_DIR"] = cfg_dir
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        # 上游 backend/CMakeLists.txt 用 find_package(ZLIB QUIET)，落空就
        # download_project 内置 zlib-1.3.1.tar.gz。该 ExternalProject 的 stamp
        # 步骤在 OHOS 上不稳定：全新构建目录实测报
        # `cd .../backend/zlib-build: No such file or directory` →
        # "Download step for zlib failed: 2"（同一份源码的增量构建目录却能过）。
        # 本配方不走 CMakeDeps（Qt6 是 cmake_find_mode=none，逐组件 _DIR 注入），
        # 故显式把图里 zlib 包的目录作为查找提示给 FindZLIB；探针实测
        # ZLIB_FOUND=TRUE 且指向该包。上游走到这条分支即绕开上述不稳定路径。
        try:
            zlib_pkg = self.dependencies["zlib"].package_folder
        except KeyError:
            zlib_pkg = None
        if zlib_pkg:
            zlib_inc = os.path.join(zlib_pkg, "include")
            if os.path.isfile(os.path.join(zlib_inc, "zlib.h")):
                tc.cache_variables["ZLIB_ROOT"] = zlib_pkg
                tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib_inc
                for lib_name in ("libz.a", "libz.so", "libz.dylib"):
                    lib_path = os.path.join(zlib_pkg, "lib", lib_name)
                    if os.path.isfile(lib_path):
                        tc.cache_variables["ZLIB_LIBRARY"] = lib_path
                        break
        # OHOS SDK 的 libc++ 15.0.4（_LIBCPP_VERSION=15004）在 C++20 下未启用
        # __cpp_lib_ranges，libosmscout 的 DescriptionService.cpp 用
        # std::views::transform 会报 "no member named 'views' in namespace 'std'"。
        # 上游开关 _LIBCPP_ENABLE_EXPERIMENTAL 把 __cpp_lib_ranges 提升到
        # 201811L（实测全新构建目录 189 对象 0 错误）。
        tc.extra_cxxflags.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
            # OHOS 适配版 conan 把 os=OHOS 映射成 CMAKE_SYSTEM_NAME=HarmonyOS，
            # CMake 因此不定义 UNIX（探针实测 UNIX=[]）。osmin 的 CMakeLists 用
            # if(UNIX) 登记必需源文件 src/signalhandler.cpp，该分支被跳过会让整个
            # 编译单元静默消失（含 moc 输出），直到链接 osmin 可执行文件才报
            # SignalHandler::* 与 staticMetaObject 未定义。显式恢复 UNIX 语义。
            tc.cache_variables["UNIX"] = "ON"
        # 只构建桌面/设备主程序：模拟器需要额外的 Qt6 组件，不参与打包
        tc.cache_variables["BUILD_SIMULATOR"] = False
        tc.cache_variables["BUILD_DEVICE_MOBILE"] = False
        tc.cache_variables["INSTALL_TESTS"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        # 必须在 configure 之前：补丁改的是 libosmscout-client-qt，而 configure 阶段
        # 上游 backend/CMakeLists.txt 会再施打它自带的 libosmscout_4.patch（同一文
        # 件的不同区域，互不重叠）。
        apply_conandata_patches(self)
        # 构建期上游会执行 Qt 自带的代码生成工具（qt6_add_repc_sources 调用
        # qtremoteobjects 包 libexec/repc，生成 rep_servicemessenger_*.h）。这些
        # 二进制无 RUNPATH，运行时只能靠 LD_LIBRARY_PATH 找 libQt6Core.so.6；而
        # conan 的构建环境只带 profile buildenv 与 tool_requires，host 依赖的 lib
        # 目录不在其中 → repc 以 "Error loading shared library libQt6Core.so.6"
        # 退出 127，代码生成目标失败（实测 make[2] build.make:391 Error 127）。
        # 处理同 ausweisapp/qtbase 系配方：把依赖包自身的 lib 目录前置进
        # LD_LIBRARY_PATH。只指向 conan 缓存内的包目录，不触碰共享系统前缀（R49）。
        build_env = Environment()
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            dep_lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(dep_lib):
                build_env.prepend_path("LD_LIBRARY_PATH", dep_lib)
        with build_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
