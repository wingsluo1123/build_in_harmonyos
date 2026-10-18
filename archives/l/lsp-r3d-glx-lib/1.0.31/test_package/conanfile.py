#!/usr/bin/env python3
"""Conan test_package — lsp-r3d-glx-lib 消费者测试（L1）.

OHOS ELF 执行需有效代码签名：消费者二进制构建后无签名，test() 内先自签名
再执行。VirtualBuildEnv 把 profile 的 [buildenv]（OHOS SDK llvm/lib 的
LD_LIBRARY_PATH）聚合进 conanbuild.sh：本机 brew 版 cmake/clang++ 运行时
需要 libc++_shared.so。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LspR3dGlxLibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_if_needed(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(signer):
            return
        # strip a possibly stale signature section; missing is fine
        self.run(f'llvm-objcopy --remove-section=.codesign "{path}" "{path}"',
                 ignore_errors=True)
        self.run(f'"{signer}" sign -selfSign 1 -inFile "{path}" -outFile "{path}"')

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_lsp-r3d-glx-lib")
        self._sign_if_needed(exe)
        self.run(f'"{exe}"', env="conanrun")
