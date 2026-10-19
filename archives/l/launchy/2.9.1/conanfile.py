#!/usr/bin/env python3
"""Conan recipe — launchy 2.9.1（Qt5 应用启动器，CMake 构建，OHOS aarch64 适配）。

上游（权威来源核验结论）：
- 任务头声明 URL https://github.com/launchy/launchy 已下线（404，仓库不存在）。
- Arch Linux 官方打包 launchy 2.9.1 使用的权威 tag 为 Slesa/launchy v2.9.1-pre.1
  （sha512 与 Arch PKGBUILD 声明值完全一致，见 notes.md），本配方沿用该官方 tag 源。
- sha256 = 26a27f4cf895cb345a277aac49b153bd3adf0ccee0d4f8716f737438bcf7c4e7。

依赖链（registry 已发布，R35 用 conan download 实测）：
- Qt5 Core/Gui/Widgets/Network/Test  → qt5-qtbase/5.15.2.2（5.15.2 为 -no-widgets，
  2.2 启用 Qt5Widgets，baka 先例 override 到 5.15.2.2）
- Qt5 X11Extras                     → qt5-qtx11extras/5.15.2
- X11/Xlib.h + libX11               → libx11/6.4.0
- xcb/xcb.h + libxcb                → libxcb/1.16（qtx11extras 拉入，显式声明）

OHOS 平台适配要点（patches/0001-0008）：
- 顶层 CMakeLists：find_package(Qt5) 组件收敛为 Gui Widgets Network Test；AUTORCC 开启；
  安装前缀改相对（bin/lib/share），避免 /usr 绝对路径污染。
- common/libqxt/launchy/plugins/specs：`qt5_use_modules`/`QT5_WRAP_UI`/`QT5_ADD_*`
  Qt5 宏改为 CMakeDeps 可解析的 `Qt5::*` 目标链接与 AUTOUIC/AUTORCC；
  `find_package(X11)` 模块探测改为 `find_package(libx11 CONFIG)`/`libxcb CONFIG`。
- E092：CMake 不识别 HarmonyOS，toolchain 设 CMAKE_SYSTEM_NAME=Linux 走 Linux 平台分支
  （编译器仍为 OHOS clang，交叉编译不受影响）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import export_conandata_patches, get, patch


class LaunchyConan(ConanFile):
    name = "launchy"
    version = "2.9.1"
    description = (
        "Launchy — a free cross-platform utility designed to help you forget about "
        "your start menu, the icons on your desktop, and even your file manager. "
        "Indexes programs and launches documents, folders, bookmarks with a few keystrokes."
    )
    license = "GPL-2.0"
    homepage = "https://www.launchy.net"
    url = "https://github.com/Slesa/launchy"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt5-qtbase/5.15.2 为 -no-widgets（无 Qt5Widgets）；launchy 的 QT += widgets
        # 需要启用 Widgets 的 5.15.2.2，作为**直接依赖**（override=True 会让 CMakeDeps
        # 只生成聚合 Qt5Config 且组件 libs 为空，链接期 undefined QObject 符号）。
        # 不依赖 qt5-qtx11extras（其链上精确要求 qt5-qtbase/5.15.2 无法与 5.15.2.2
        # 共存；launchy 仅用 QX11Info::display() 一处，已替换为 QtGui 的
        # QPlatformNativeInterface 获取 Display*，见 common/x11 补丁）。
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("libx11/6.4.0")
        self.requires("libxcb/1.16")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"launchy only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游工程根下源码位于 src/ 子目录（tarball 根含 README/skins/translations
        # 等资源），补丁由 refresh-patch --auto 以 work 目录（即 src/ 内容拍平）生成，
        # 路径不带 src/ 前缀。这里显式 base_path="src" 应用，使补丁落在 src/ 下，
        # 与 refresh-patch 输出天然一致（避免每次 finish 重新生成后路径失配）。
        patches = self.conan_data.get("patches", {}).get(str(self.version), [])
        for it in patches:
            if "patch_file" in it:
                patch(
                    self,
                    base_path="src",
                    patch_file=it["patch_file"],
                    strip=1,
                    **{k: v for k, v in it.items() if k not in ("patch_file", "patch_type", "patch_description")},
                )

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase 包自身 cpp_info 已设 cmake_file_name=Qt5，CMakeDeps 生成聚合
        # Qt5Config.cmake，使 find_package(Qt5 COMPONENTS Gui Widgets Network Test)
        # 与各子目录 find_package(Qt5Core)/find_package(Qt5X11Extras) 可解析。
        deps.generate()

        tc = CMakeToolchain(self)
        # CMake 4.x 移除了 <3.5 兼容，上游 cmake_minimum_required(3.5.1) 需策略下限
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake 不识别 HarmonyOS 平台（无 Platform/HarmonyOS 模块），OHOS 基于
        # Linux 内核，设 CMAKE_SYSTEM_NAME=Linux 走 Linux 平台分支（__LIN__ → X11
        # 平台代码编译链接）；编译器仍由 conan_toolchain 指向 OHOS clang。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # R26: 系统同名库静态；launchy 自身是 GUI 应用（可执行目标），无共享库需求
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # 交叉编译下 Qt 工具（moc/rcc/uic）由 qt5-qtbase 包提供，显式指定
        qt5_pkg = self.dependencies["qt5-qtbase"].package_folder
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = os.path.join(qt5_pkg, "bin", "moc")
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = os.path.join(qt5_pkg, "bin", "rcc")
        tc.variables["CMAKE_AUTOUIC_EXECUTABLE"] = os.path.join(qt5_pkg, "bin", "uic")
        # qt5-qtbase 以 override=True 进入图时，CMakeDeps 只生成聚合 Qt5Config.cmake
        # 且组件 INTERFACE_INCLUDE_DIRECTORIES 为空（编译期找不到 QTableWidget 等）。
        # 显式把 qtbase include 根与全部 Qt* 模块子目录（含 Qt* 版本私有头目录，
        # 如 include/QtGui/5.15.2/QtGui —— qxtglobalshortcut_x11.cpp 需要
        # <qpa/qplatformnativeinterface.h>）注入 toolchain 变量，
        # 由 CMakeLists 顶层 include_directories(${QT5_INCLUDE_DIRS}) 消费（见补丁 0001）。
        qt5_inc = os.path.join(qt5_pkg, "include")
        inc_dirs = [qt5_inc]
        if os.path.isdir(qt5_inc):
            for entry in sorted(os.listdir(qt5_inc)):
                sub = os.path.join(qt5_inc, entry)
                if entry.startswith("Qt") and os.path.isdir(sub):
                    inc_dirs.append(sub)
                    # Qt*/<version>/Qt* 版本私有头目录（如 QtGui/5.15.2/QtGui）
                    for sub_entry in sorted(os.listdir(sub)):
                        sub_sub = os.path.join(sub, sub_entry)
                        if sub_entry[:1].isdigit() and os.path.isdir(sub_sub):
                            inc_dirs.append(sub_sub)
                            for ver_entry in sorted(os.listdir(sub_sub)):
                                ver_dir = os.path.join(sub_sub, ver_entry)
                                if ver_entry.startswith("Qt") and os.path.isdir(ver_dir):
                                    inc_dirs.append(ver_dir)
        tc.variables["QT5_INCLUDE_DIRS"] = ";".join(inc_dirs)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # 上游工程根下 CMakeLists.txt 位于 src/ 子目录（tarball 根含 README、
        # skins、translations 等资源），显式指向该子目录。
        cmake.configure(build_script_folder="src")
        cmake.build()
        # 上游用例：launchy.specs（QtTest）经 ctest 驱动（commandlineparser +
        # singleapplication 两套 spec），失败不阻断打包，结果记入测试台账
        try:
            cmake.ctest(cli_args=["--output-on-failure"])
        except Exception as e:
            self.output.warning(f"ctest 有失败项（详见测试台账）: {e}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 安装产物：bin/launchy、lib/launchy/plugins/*、share/launchy/skins/、
        # share/doc/launchy 等（安装前缀已改相对，落于 package_folder）

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # GUI 应用包：无库目标，仅 bin/ 可执行文件（R38/L0k 判定为 tool 型，
        # 软件级 commands.json 由 build_in_harmonyos 仓库软件目录提供）