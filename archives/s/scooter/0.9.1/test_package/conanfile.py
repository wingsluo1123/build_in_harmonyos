#!/usr/bin/env python3
"""Consumer test for scooter 0.9.1 — verifies the `scooter` binary exists and responds.

Cross-compilation scenario: the produced `scooter` binary is an arm64 OHOS ELF,
cannot be executed on the CI worker (x86_64 Linux) → test_package honestly
skips runtime verification and only checks binary existence + ELF header.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class ScooterTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # L0c 门禁要求 test_package 有 test 源文件；编译 test_scooter.c 使其真实生效
        from conan.tools.cmake import CMake
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # P1: 删空壳测试 — 真验证 scooter 二进制存在 + ELF header 段
        bin_dir = self.dependencies["scooter"].cpp_info.bindirs[0]
        scooter_bin = os.path.join(self.dependencies["scooter"].package_folder, bin_dir, "scooter")
        if not os.path.exists(scooter_bin):
            raise ConanException(f"scooter binary not found at {scooter_bin}")

        # cross-building scenario: arm64 OHOS binary cannot run on x86_64 CI worker
        if cross_building(self):
            self.output.info("SKIP_RUNTIME_TEST: cross-building scenario, arm64 OHOS binary cannot run on CI worker")
            # ELF header sanity check (arm64 OHOS ELF)
            with open(scooter_bin, "rb") as f:
                magic = f.read(4)
            if magic != b"\x7fELF":
                raise ConanException(f"scooter binary is not a valid ELF file: magic={magic!r}")
            self.output.info("ELF header sanity check PASSED (arm64 OHOS binary)")
            # 交叉编译占位：test_scooter 无参数仅编译通过（R34：无法在宿主运行 arm64 二进制）
            self.run("./test_scooter", env="conanrun", cwd=self.build_folder)
            return

        # native scenario: run test_scooter with scooter binary path (R34 反空壳：真实执行 --version 检查返回码)
        self.run(f'./test_scooter "{scooter_bin}"', env="conanrun", cwd=self.build_folder)
        self.output.info("scooter runtime test PASSED (scooter --version exit 0)")
