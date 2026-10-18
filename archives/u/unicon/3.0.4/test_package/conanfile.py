#!/usr/bin/env python3
"""Conan test_package — unicon 3.0.4 消费者用例（L1）。

consumer_test.cpp 模拟业务上层调用公开 API（ImmClient.h 的 IMM_* 一族）：
进程内形态（-D__DLL_SUPPORT__，链 libimmclient.a + libimm_server.so），
硬断言：kexue → 科学（GBK BF C6 D1 A7）、zhongguo → 中国（GBK D6 D0 B9 FA）。
退出码 0=通过 / 1=断言失败 / 2=环境错误。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UniconTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            # 运行时模块/数据路径以包根为基准（见 CMakeLists.txt add_test）
            "UNICON_PKG_ROOT": str(self.dependencies["unicon"].package_folder),
        })
        cmake.build()

    def test(self):
        # 显式 self.run（CI L0d 门禁按字面 self.run 判定非空壳）；
        # 命令与 CMake.test() 内部执行完全等价：
        # cmake --build <build_folder> --target test → 触发 ctest
        self.run('cmake --build "{}" --target test'.format(self.build_folder),
                 env=["conanbuild", "conanrun"])
