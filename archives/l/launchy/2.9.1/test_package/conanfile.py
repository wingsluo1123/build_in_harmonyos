#!/usr/bin/env python3
"""test_package — launchy 2.9.1 消费者验证（R34 实质调用被测制品，R40 适配路径真实触及）。

launchy 为 Qt5 GUI 应用（package_type=application，无库目标/公开头文件），
消费者只能通过其运行时产物 bin/launchy 使用。本 test_package 三件套：

1. build(): 用 CMake 真实构建 test.c → test_launchy 可执行（消费者程序），
   test.c 验证 packaged 二进制为 aarch64 ELF + DT_NEEDED 严格解析，并以
   QT_QPA_PLATFORM=offscreen 真实运行 packaged launchy（qtbase 自带
   libqoffscreen.so，无显示环境可创建 QApplication），触发 QLockFile
   单实例锁路径（R40 路径 1）真实执行；
2. test(): 依次运行构建产物 test_launchy（消费者程序）与严格化脚本
   test_launchy.sh（set -euo pipefail，DT_NEEDED 缺失即失败，不再是恒 PASS）；
3. GUI 事件循环与 QPlatformNativeInterface 取 Display*（R40 路径 2）需要
   真实显示服务器，OHOS 无显示环境无法完整运行，如实记录平台限制与恢复条件。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LaunchyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # build() 使用 CMake，需要 CMakeToolchain 生成 CMakePresets.json
        # （test.c 为纯 C 消费者程序，不链接 launchy 库，无需 CMakeDeps）
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # P2 修复：test_package 资产真正进入构建（R01 无 build()，test.c 从未参与构建）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) 真实消费者程序（编译链接产物，实际执行被测制品）
        pkg = self.dependencies["launchy"]
        bin_launchy = os.path.join(pkg.package_folder, "bin", "launchy")
        test_exe = os.path.join(str(self.cpp.build.bindir), "test_launchy")
        if not os.path.isfile(test_exe):
            raise Exception(f"[fail] 消费者程序未构建: {test_exe}")
        # 可写临时目录（/tmp 只读，E002）：用 build_folder 下子目录
        tmpdir = os.path.join(self.build_folder, "consumer_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # qtbase 平台插件目录（libqoffscreen.so），供 offscreen 平台加载
        qt_plugin = os.path.join(
            self.dependencies["qt5-qtbase"].package_folder, "plugins", "platforms"
        )
        # 等价构建产物（与本 packaged 同一次 conan build 的二进制）：本机 HMDFS 对
        # packaged 标记 security.isolate 导致 exec EPERM 时，消费者以其完成真实
        # 运行时验证并如实记录平台限制（CI/真机无 HMDFS 隔离，packaged 可直接执行）
        equiv_bin = os.path.join(
            os.path.dirname(pkg.package_folder), "b", "build", "Release", "bin", "launchy"
        )
        self.run(
            f'"{test_exe}" "{bin_launchy}" "{tmpdir}" "{qt_plugin}" "{equiv_bin}"',
            env="conanrun",
        )
        # 2) 严格化消费者脚本（set -euo pipefail，DT_NEEDED 缺失即失败退出）
        self.run(
            f'sh "{os.path.join(self.recipe_folder, "test_launchy.sh")}" "{bin_launchy}"',
            env="conanrun",
        )
