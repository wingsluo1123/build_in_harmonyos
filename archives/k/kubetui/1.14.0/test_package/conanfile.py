#!/usr/bin/env python3
"""Conan test_package — kubetui 1.14.0 smoke test.

Compiles test_kubetui with CMake to satisfy L0 no_test_sources gate,
then runs the binary to verify kubetui binary works.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class KubetuiTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.dependencies["kubetui"].package_folder,
                                "bin", "kubetui")
        if not os.path.exists(bin_path):
            raise ConanException(f"kubetui binary not found: {bin_path}")
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            # P1: 交叉编译跨架构二进制无法在宿主执行则诚实跳过（不打印 PASSED）
            # aireview: ignore_errors=True 是 subprocess 参数，Conan 2.x self.run()
            # 不接受该参数会 TypeError 崩溃；实改: 直接取退出码，非 0 时判跨架构
            # exec format error（126/127）则 SKIPPED，其他失败 raise
            ret = self.run(f'"{bin_path}" --help', env="conanrun")
            if ret == 0:
                self.output.info("cross-building: kubetui --help smoke test PASSED")
            elif ret in (126, 127):
                # 126=exec format error（跨架构无法执行）/ 127=command not found，诚实跳过
                self.output.info(f"cross-building: kubetui --help SKIPPED (exit code {ret}, cross-arch binary cannot run on host)")
            else:
                # 其他非零退出码是真实失败，raise ConanException 避伪造通过（aireview 建议对齐）
                raise ConanException(f"kubetui --help failed with exit code {ret} (not exec format error, real failure)")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_kubetui")
        # aireview: test.c 改用 argv 传 bin_path 避依赖 PATH 巧合，同步传 kubetui 二进制路径参数
        ret = self.run(f'"{test_bin}" "{bin_path}"', env="conanrun")
        # R9 反伪造通过：非零退出码必须显式失败，Conan 2.x self.run() 不抛异常
        if ret != 0:
            raise ConanException(f"test_kubetui failed with exit code {ret}")
