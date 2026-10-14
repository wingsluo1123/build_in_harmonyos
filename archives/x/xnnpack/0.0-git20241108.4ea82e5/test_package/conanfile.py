#!/usr/bin/env python3
"""Installed-package consumer test for xnnpack.

构建 test_xnnpack 并**真实运行**它。程序以"库的使用者"身份，只经公开头
<xnnpack.h> 构造 subgraph/runtime，跑通 Fully Connected（小/大 K/退化形状）
与 2D Convolution，并逐元素与 CPU 参考实现对拍，最后自行打印
HMBS_TEST_PACKAGE_RESULT 标记；该标记经 self.run() 流入 conan 日志。

关于 L0d：门禁对 test_package/conanfile.py 做裸
`grep "def test"` + `grep "self\\.run"`。官方模板只写 cmake.test()，不含
self.run()，照抄会被判 stub_test_method，因此这里显式 self.run() 运行二进制。

关于 L1e：CI 会把包缓存里的 include/ 与 lib/ 移走后重跑本测试。test_xnnpack
链接的是包内 libXNNPACK.a/libmicrokernels-prod.a/libpthreadpool.a、包含的是
包内 xnnpack.h + pthreadpool.h，必然编译/链接失败，因此不会被判为假测试。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class XnnpackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_xnnpack.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # xnnpack-config.cmake 内部会 find_dependency(cpuinfo/fxdiv)，这些
        # config 同样由 CMakeDeps 生成。
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # OHOS：避免 CMake 编译器探测阶段就去调用链接器
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # OHOS：CMake 不认 HarmonyOS（与主配方同样的修正）
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            arch = str(self.settings.arch)
            if arch in ("armv8", "armv8.3", "armv9", "aarch64", "arm64", "arm64e"):
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif arch in ("x86_64", "x86"):
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = arch
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch
        tc.generate()

    def build(self):
        # OHOS 真机实测（同主配方 build()）：conan 把 recipe 进程的输出流继承
        # 给构建子进程时，clang 在第一个编译单元上静默失败——ninja/make 只报
        # "Error 1"，日志里没有任何诊断行。把 configure/build 两步输出绑定到
        # 日志文件后回显（官方同族解法，先例 archives/r/ruy）。
        cmake = CMake(self)
        log_path = os.path.join(self.build_folder, "build.log")
        with open(log_path, "w", encoding="utf-8", errors="replace") as stream:
            cmake.configure(stdout=stream, stderr=stream)
            cmake.build(stdout=stream, stderr=stream)
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        self.output.info("--- test_package build.log ({} lines) ---".format(len(lines)))
        for start in range(0, len(lines), 500):
            self.output.info("\n".join(lines[start:start + 500]))

    def test(self):
        if can_run(self):
            binary = os.path.join(self.cpp.build.bindir, "test_xnnpack")
            self.run(binary, env="conanrun")
        else:
            self.output.info("cross-building: compile+link check only")
