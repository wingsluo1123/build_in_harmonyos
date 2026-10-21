#!/usr/bin/env python3
"""test_package for ktx 1.45 (Conan L1 test).

ktx is a QuakeWorld server mod shipped as a dlopen-able native module, so the
consumer test does the same thing the QuakeWorld server does:

  1. build(): resolve the package through Conan (CMakeDeps + CMakeToolchain)
     and compile against it -- proves the recipe's generated CMake config
     (ktx::ktx) is consumable by a downstream CMake project.
  2. test(): run the test binary against the packaged lib/qwprogs.so. The
     binary dlopen()s it with RTLD_NOW, resolves dllEntry/vmMain, performs the
     server<->mod handshake and asserts the HarmonyOS-specific ELF properties.

Upstream ktx 1.45 ships no automated test suite (no tests/ directory anywhere in
the tree; .github/workflows/main.yml only builds), so every assertion here is
OHOS-adaptation self-authored. See MANIFEST.yml for the breakdown.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KtxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["ktx"]
        so_path = os.path.join(dep.package_folder, "lib", "qwprogs.so")
        if not os.path.isfile(so_path):
            raise RuntimeError(
                "packaged module not found at {} -- recipe package() did not "
                "ship lib/qwprogs.so".format(so_path)
            )

        test_bin = os.path.join(self.cpp.build.bindir, "ktx_module_test")
        if not os.path.isfile(test_bin):
            raise RuntimeError("test binary not built: {}".format(test_bin))

        cmd = '"{}" "{}"'.format(test_bin, so_path)
        self.run(cmd, env="conanrun")