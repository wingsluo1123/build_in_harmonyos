#!/usr/bin/env python3
"""Conan test_package for ECM 6.28.0 — L1 test.

Verifies that ECM CMake modules are correctly installed and discoverable
via find_package(ECM). The test compiles a C++ program that includes
ECM macros and asserts the installed version matches the expected one.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class TestECMConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The HNP cmake binary needs libc++_shared.so from the SDK
        # aarch64-linux-ohos lib dir; persist the runtime env so the
        # configure/build steps below can start cmake (same as main recipe).
        self._sdk_runtime_env().vars(self).save_script("sdk_runtime_env")

    def build(self):
        cmake = CMake(self)
        ecm_prefix = self.dependencies["ecm"].package_folder
        cmake.configure(variables={"ECM_PACKAGE_PREFIX": ecm_prefix})
        cmake.build()

    def test(self):
        test_program = os.path.join(self.cpp.build.bindir, "test_ecm")
        with self._sdk_runtime_env().vars(self).apply():
            self.run(test_program, env="conanrun")

    def _sdk_runtime_env(self):
        env = Environment()
        sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        sdk_libs = sorted(
            glob.glob(os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib"))
        )
        for lib_dir in sdk_libs:
            env.prepend_path("LD_LIBRARY_PATH", lib_dir)
            sub = os.path.join(lib_dir, "aarch64-linux-ohos")
            if os.path.isdir(sub):
                env.prepend_path("LD_LIBRARY_PATH", sub)
        return env
