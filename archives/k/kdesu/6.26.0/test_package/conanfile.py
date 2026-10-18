#!/usr/bin/env python3
"""Conan test_package for kdesu 6.26.0.

Verifies that the adapted KF6Su library is consumable on OHOS: the exported
CMake package (KF6Su -> KF6::Su) is found, the SuProcess configuration paths
behave (default su / sudo / doas / unknown fallback), SshProcess links, and
the installed kdesu_stub helper answers the protocol installation check
(R34: real API usage, no print-only stub).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KDesuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # KF6SuConfig.cmake chain-finds KF6Pty, and the consumer also uses
        # KConfig directly. Those packages install their own real CMake configs
        # (cmake_find_mode=none, so CMakeDeps does not generate stand-ins), so
        # every dependency's lib/cmake dir must be on CMAKE_PREFIX_PATH for the
        # find_package()/find_dependency() chains to resolve.
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via LD_LIBRARY_PATH.
        # Prepend it so CMake's TryCompile can link. Must not clobber conanbuild
        # env on other hosts. On OHOS also prepend /system/lib64 after the SDK
        # path: the sandbox LD_LIBRARY_PATH carries an incompatible
        # libc++_shared.so that would otherwise shadow the compatible one (the
        # recipe's _cmake_build_env applies the same fix).
        env = Environment()
        for sdk_llvm_lib in sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
        ):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        # Match the recipe's runtime environment: dependency lib dirs are
        # prepended (not appended after the inherited value), and on OHOS
        # /system/lib64 goes first so the compatible libc++_shared.so wins
        # over the sandbox copy (audiocd/baloo/czmq test_package precedent).
        for p in self.dependencies.values():
            if p.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(p.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kdesu"),
                env="conanrun",
            )
