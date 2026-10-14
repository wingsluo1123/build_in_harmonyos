#!/usr/bin/env python3
"""Conan test_package for libusbauth-configparser 1.0.5 — L1 consumer test.

Two consumers run against the packaged library:

  - test_libusbauth_configparser      : exercises the exported public API
                                        (parameter/operator string<->enum
                                        tables, Data construction, sub_length
                                        clamping, graceful failure when the
                                        config file is absent).
  - test_libusbauth_configparser_ohos : HarmonyOS-specific assertions (rule12):
                                        the re-signed libusbauth-configparser.so.1
                                        loads on the OHOS runtime and its entry
                                        points resolve; plus a full flex/bison
                                        parse round-trip driven through the
                                        $USBAUTH_CONFIG-overridable path (the
                                        HarmonyOS /etc read-only workaround).

The generate() step mirrors vdeplug/4.0.1's test_package: the shared
ohos-aarch64 profile pins tools.build:compiler_executables to
/data/service/hnp/bin/clang, which is not present on every worker, so the
generated CMakeToolchain is rewritten to a compiler that actually exists.
VirtualRunEnv is generated explicitly because self.run(env="conanrun") below
requires the conanrun script.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class LibusbauthConfigparserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test.c", "test_ohos.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable(
                "c", "clang"
            )
        tc.generate()
        if str(self.settings.os) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Explicit self.run() so CI L0d does not flag this as a stub test.
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libusbauth_configparser"),
                 env="conanrun")
        self.run(os.path.join(bindir, "test_libusbauth_configparser_ohos"),
                 env="conanrun")

    def _compiler_executable(self, key, fallback_name):
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
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
