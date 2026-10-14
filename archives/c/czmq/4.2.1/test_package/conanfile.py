#!/usr/bin/env python3
"""Test package for czmq — verifies the library is usable."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class CzmqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def export_sources(self):
        # 测试源文件必须随 test_package 导出：CI L0c 门禁要求 test_package/
        # 下存在 .c/.sh 测试源（E255/E308），导出同时保证缓存侧可复现。
        for name in ("CMakeLists.txt", "test_czmq.c", "test_ohos_flow.c", "test_ohos.sh"):
            copy(self, name, src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires(self.tested_reference_str)
        # czmq public headers (czmq_prelude.h) #include "zmq.h". Conan strips
        # headers/libs data of 2nd-level (transitive) dependencies in
        # CMakeDeps, so declare zeromq directly to get its include dir.
        self.requires("zeromq/4.3.5")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # conanrun env：test_ohos.sh 与消费者二进制依赖 LD_LIBRARY_PATH 闭合
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 保留既有消费者断言测试（版本宏 / inproc 回环 / zframe / zmsg）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_czmq"), env="conanrun")
        # rule12 鸿蒙特有端到端消费者用例（非纯断言）：平台探测 + 产物断言 +
        # 真实功能流（zconfig 文件落盘/重载回环 + REQ/REP 环回 TCP 消息流），
        # 由 test_ohos.sh 调用 test_ohos_flow 完成。
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        script = os.path.join(self.source_folder, "test_ohos.sh")
        if os.path.isfile(script):
            lib_dir = os.path.join(self.dependencies["czmq"].package_folder, "lib")
            consumer = os.path.join(self.cpp.build.bindirs[0], "test_ohos_flow")
            work_dir = os.path.join(self.build_folder, "ohos_flow_work")
            self.run('"{}" "{}" "{}" "{}" "{}"'.format(
                shell, script, lib_dir, consumer, work_dir), env="conanrun")
            self.output.info(
                "HarmonyOS-specific end-to-end consumer flow OK (rule12)")
