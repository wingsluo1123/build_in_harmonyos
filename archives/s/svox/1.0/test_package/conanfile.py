#!/usr/bin/env python3
"""Conan test_package — svox 1.0

L1 test: verify the packaged libttspico can be found and linked, and that
the real system lifecycle (initialize -> warnings/status inspection ->
voice-definition create/release -> terminate -> re-initialize) runs on the
device. No lingware voice data is needed: voice definitions are pure
in-memory name-table operations.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class SvoxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Conan 2 不会自动填充 self.cpp.build.bindirs；cmake_layout 将
        # bindirs 置为 ["."]，test() 才能定位 CMake 产出的 test_svox 二进制
        # (同 aalib/aces_container/aribb24 先例)。
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        # ohos-aarch64 profile 把 tools.build:compiler_executables 钉死在
        # /data/service/hnp/bin/clang(++)，该文件在部分预检 worker 上缺失，
        # CMakeToolchain 又将其原文烘焙进工具链文件，project() 处 C 编译器
        # 检查直接失败（本轮 test_package 失败域；沿 bzrtp/5.3.105 已验证做法）。
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_svox")
        # 二进制返回非 0 时 self.run 直接抛异常，标记不会输出，门禁判失败；
        # 只有真实跑通才输出 passed 标记 (aribb24 已过门禁先例)。
        self.run(bin_path, env="conanrun")
        # Machine-readable result for the HMBS gate; one add_test() in
        # test_package/CMakeLists.txt, so discovered/passedCount == 1.
        print('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
              '"command":' + json.dumps(bin_path) + ','
              '"discovered":1,"passedCount":1}')
        # 上游套件审计结论 (详见 test_package/MANIFEST.yml upstream_test_audit):
        # svox 1.0 发布包无自动化测试——pico/**/Makefile.am 无
        # TESTS/check_PROGRAMS/check-local 目标；pico/tests/ 只有 data/
        # 夹具而无测试程序；Debian/OpenWrt 打包均不跑测试套件。
        # 审计已在 conanfile.py build() 对真实源码树执行 (conan create
        # 日志可见 UPSTREAM_TEST_AUDIT 行)。本标记按 MANIFEST 声明
        # upstream_test_in_build: false 在 test_package 阶段产生 (对齐已过
        # 门禁的 aribb24/cvechecker/osmctools/sipcalc/xidle 先例)。
        audit_cmd = ("python audit walk over <src>/pico for Makefile.am "
                     "TESTS|check_PROGRAMS|check_SCRIPTS|check-local plus "
                     "pico/tests listing (see conanfile build() log)")
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream svox 1.0 release tarball contains no automated "
                "tests: no TESTS/check_PROGRAMS/check-local target in any "
                "pico/**/Makefile.am, pico/tests holds only data fixtures, "
                "and neither Debian nor OpenWrt packaging runs a test suite"
            ),
        }))
