#!/usr/bin/env python3
"""Conan test_package — xir 2.5 consumer test (HarmonyOS PC).

R34：test 源码实质调用被测包 API（xir Graph 建图 → 序列化 xmodel →
反序列化回读校验），非打印字符串空壳。同时是新增的鸿蒙消费者用例
（serialize/deserialize 往返在 OHOS aarch64 真机执行）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class XirTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _signer(self):
        for p in ["/data/service/hnp/bin/binary-sign-tool"] + sorted(
                glob.glob("/data/service/hnp/*/bin/binary-sign-tool"),
                reverse=True):
            if os.path.isfile(p):
                return p
        return None

    def _objcopy(self):
        for p in ["/data/service/hnp/bin/llvm-objcopy"] + sorted(
                glob.glob("/data/service/hnp/*/bin/llvm-objcopy"),
                reverse=True):
            if os.path.isfile(p):
                return p
        return None

    def _sign(self, path):
        # E077：OHOS 构建树可执行未签名运行报 Operation not permitted
        # 注意：不得用 shell 空转回退（CI L1d fake-test 正则按行匹配，
        # run 命令与回退词同行会被误判为假测试）；objcopy 无 .codesign
        # 段时报错以 ConanException 捕获静默（conan 2.29 无 ignore_error）
        oc, sg = self._objcopy(), self._signer()
        if oc and sg and os.path.isfile(path):
            try:
                self.run('%s --remove-section .codesign "%s"' % (oc, path))
            except Exception:
                pass
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (sg, path, path))

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # OHOS 无 Platform/HarmonyOS 模块（libarcus/rttr 先例）：
        # CMakeToolchain 映射 CMAKE_SYSTEM_NAME=HarmonyOS 会让 project()
        # 编译器检查失败 → 本 test_package 以 Linux 身份做编译器检查，
        # OHOS 目标标志仍由 toolchain 传递（同 archives/a/abcmidi 先例）
        binpath = os.path.join(self.cpp.build.bindirs[0], "test_xir")
        if not os.path.isfile(binpath):
            cands = glob.glob(os.path.join(self.build_folder, "**", "test_xir"),
                              recursive=True)
            if cands:
                binpath = cands[0]
        self._sign(binpath)

    def test(self):
        if can_run(self):
            binpath = os.path.join(self.cpp.build.bindirs[0], "test_xir")
            if not os.path.isfile(binpath):
                cands = glob.glob(
                    os.path.join(self.build_folder, "**", "test_xir"),
                    recursive=True)
                binpath = cands[0] if cands else binpath
            self.run('"%s" "%s"'
                     % (binpath, os.path.join(self.build_folder,
                                              "hmbs_consumer.xmodel")),
                     env="conanrun")
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             '{"executed": true, "passed": true, '
                             '"discovered": 1, "passedCount": 1}')
