#!/usr/bin/env python3
"""Conan test_package — retro-gtk 1.0.2 消费者侧验证（R34 真实 API 使用）。

两段测试：
  1. consumer 程序：链接被测库，用 RetroCore 公开 API 启动被测包内的
     retro-runner、挂载一个假 Libretro 核心、跑 3 帧并逐像素校验视频输出契约
     （覆盖 runner 进程 + 私有 GDBus IPC + memfd 帧缓冲 + RetroPixdata 全链路）；
  2. test_ohos.sh：鸿蒙专项断言（产物 ELF64/AArch64 + .codesign、无 Linux 专有
     动态依赖、soname/导出符号/头文件/.pc 齐备、设备端帧校验和确定）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class RetroGtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 消费者自己也要直接调 GLib/GdkPixbuf（断言 + 像素读回）
        self.requires("glib/2.84.0.1")
        self.requires("gtk/3.24.43")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # 消费者用 pkg-config 找被测包（retro-gtk-1.pc）与其依赖的 GLib/GdkPixbuf
        PkgConfigDeps(self).generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        consumer = os.path.join(self.build_folder, "retro-gtk-consumer")
        core = os.path.join(self.build_folder, "libretro-test-core.so")
        runner = os.path.join(package_folder, "libexec", "retro-runner")
        if not os.path.isfile(runner):  # meson 的 libexecdir 视配置而定
            runner = os.path.join(package_folder, "bin", "retro-runner")

        # 测试自建的 ELF（消费者 + 假核心）在本机同样需要有效 .codesign
        for path in (consumer, core):
            self._sign(path)

        env = "conanrun"
        self.run(f'RETRO_RUNNER_PATH="{runner}" "{consumer}" "{core}"',
                 env=env)
        self.run('bash "%s" "%s" "%s" "%s"'
                 % (os.path.join(self.recipe_folder, "test_ohos.sh"),
                    package_folder, self.build_folder, runner),
                 env=env)

    def _sign(self, path):
        """给测试自建的 ELF 重签（OHOS loader 要求有效 .codesign）。"""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        if not os.path.isfile(signer):
            return
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}"',
                     ignore_errors=True)
        shutil.copy2(path, path + ".unsigned")
        self.run(f'"{signer}" sign -inFile "{path}.unsigned" -outFile "{path}" '
                 f'-selfSign 1')
        os.remove(path + ".unsigned")
        os.chmod(path, 0o755)
