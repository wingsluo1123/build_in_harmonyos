#!/usr/bin/env python3
"""Conan test_package — git-who 1.3 smoke test.

Compiles test_git_who with CMake to satisfy L0 no_test_sources gate,
then runs the binary to verify git-who --help works.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GitWhoTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CI #16940: CMake TryCompile 阶段 clang 默认调 ohos-sdk 的
        # /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld
        # 报 xmlNewNs/xmlFree: symbol not found（该 lld 依赖 libxml2 符号缺失）→
        # linker command failed due to signal（同 klystrack CI #16923 根因）。
        # → -fuse-ld=ld 强制用系统 /data/service/hnp/bin/ld（本地实测链接成功 rc=0）。
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-fuse-ld=ld"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.dependencies["git-who"].package_folder,
                                "bin", "git-who")
        if not os.path.exists(bin_path):
            raise ConanException(f"git-who binary not found: {bin_path}")
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        # Run the compiled test binary (verifies git-who --help)
        # aireview P3: bindirs[0] 未做空列表防护 — 交叉编译场景 bindirs 可能为空致 IndexError
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_git_who build folder (bindirs) is empty — cannot locate test binary")
        test_bin = os.path.join(bindirs[0], "test_git_who")
        # aireview: test.c 改用 argv 传 bin_path 避依赖 PATH 巧合，同步传 git-who 二进制路径参数
        self.run(f'"{test_bin}" "{bin_path}"', env="conanrun")
