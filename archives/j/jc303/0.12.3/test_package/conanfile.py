#!/usr/bin/env python3
"""Conan test_package for jc303/0.12.3 — OHOS 消费式插件产物验证。

上游无任何测试套件（归档全树 grep enable_testing/add_test/catch2/gtest/
doctest/ctest/unittest 0 命中，无 tests/ 目录，Dockerfile 仅发布构建环境），
按 NO_UPSTREAM_TESTS 处理；验证主路径为消费式：

  1. bundle 布局断言（configure 期 file(GLOB) 失败即 FATAL_ERROR）：
     VST3/LV2 bundle 内唯一插件 .so、LV2 bundle ≥2 个 .ttl（juce_lv2_helper
     构建期在真机生成）；
  2. 运行期 dlopen/dlsym 探针（__OHOS__ 编译期卫兵）：VST3
     GetPluginFactory / LV2 lv2_descriptor / CLAP clap_entry —— E505 签名 +
     $ORIGIN 多级 rpath 依赖闭包（freetype/fontconfig/libxml2/alsa 实体化
     视图）在真机 dlopen 真实生效（kodi-inputstream-adaptive DRAFT
     lv2-bundle-host-side-test-pattern 同款范式，不带 GUI 运行）。

L1e 破坏性反向验证：lib/ 整体移走后 bundle 路径消失 → dlopen 必失败 →
conan test 非零（测试实质依赖被测包）。
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

TEST_CHECKS = 10


class Jc303TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["JC303_PACKAGE_DIR"] = self.dependencies["jc303"].package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        result = {
            "executed": True,
            "passed": False,
            "command": "ctest --output-on-failure -R jc303_bundle_probe",
            "discovered": TEST_CHECKS,
            "passedCount": 0,
        }
        # OHOS: /system/bin/sh (mksh) 不能直接 exec ELF，用 buildenv 的 bash 包装；
        # 同时 unset LD_LIBRARY_PATH（E505：避免压过二进制内嵌 $ORIGIN rpath）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run(f'{bash} -c "unset LD_LIBRARY_PATH; '
                     f'ctest --output-on-failure -R jc303_bundle_probe"',
                     env="conanrun")
        except Exception as exc:
            self.output.info("jc303 test_package failed: {}".format(exc))
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = TEST_CHECKS
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
