#!/usr/bin/env python3
"""Consumer test for spot/2.15.1 — named cases, real executors on the OHOS target."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class SpotConsumerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("test_package requires the OHOS target: cannot run here")

        pkg = self.dependencies["spot"].package_folder
        libso = os.path.join(pkg, "lib", "libspot.so")
        probe = os.path.join(self.cpp.build.bindirs[0], "spot_probe")

        def case(name, command):
            ok = self.run(command, env="conanrun", ignore_errors=True) == 0
            self.output.info("TEST %s: %s" % (name, "PASS" if ok else "FAIL"))
            return ok

        results = [
            # 1. 消费者二进制真实链接 libspot/libbddx 并执行 6 项 API 用例
            case("cpp_api_probe", '"%s"' % probe),
            # 2. 命令行工具版本
            case("cli_ltl2tgba_version", 'ltl2tgba --version | grep -q "2\\.15\\.1"'),
            # 3. 命令行 LTL 转换（HOA 输出）
            case("cli_ltl2tgba_translate", 'ltl2tgba -f "G F a" | grep -qi "acceptance:"'),
            # 4. 命令行等价过滤（正例）
            case("cli_ltlfilt_equivalence",
                 'ltlfilt -f "a U b" --equivalent-to="b | (a & X(a U b))" | grep -q "a U b"'),
            # 5. 产物平台形态：AArch64 共享库
            case("elf_aarch64_shared", 'readelf -h "%s" | grep -q "AArch64"' % libso),
            # 6. 产物代码签名存在（.codesign 段）
            case("codesign_present", 'readelf -SW "%s" | grep -q "\\.codesign"' % libso),
        ]
        passed = sum(1 for r in results if r)
        self.output.info("TEST SUMMARY: %d/%d passed" % (passed, len(results)))
        if passed != len(results):
            raise ConanException("spot consumer test: %d/%d cases passed" % (passed, len(results)))
