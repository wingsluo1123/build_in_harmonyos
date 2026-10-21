#!/usr/bin/env python3
"""Conan test_package for plotsauce 0-0.1 — Conan L1 official test.

Exercises the packaged `plotsauce` binary end-to-end (R34):
  1. build a helper that writes a deterministic valid Survex .3d input;
  2. run the packaged plotsauce binary on it;
  3. validate the gzip-compressed XML output with a helper linked to zlib.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class PlotsauceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt/5.15.19", visible=False)  # runtime Qt libs for the binary
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        build_dir = self.cpp.build.bindirs[0]
        sample = os.path.join(self.build_folder, "test.3d")
        out = os.path.join(self.build_folder, "out.xml.gz")
        plotsauce_bin = os.path.join(
            self.dependencies["plotsauce"].cpp_info.bindirs[0], "plotsauce")

        # The binary links Qt5 dynamically; make the Qt lib dir and the OHOS
        # SDK libc++_shared.so discoverable while running it.
        env = Environment()
        qt_lib = os.path.join(self.dependencies["qt"].package_folder, "lib")
        env.prepend_path("LD_LIBRARY_PATH", qt_lib)
        llvm_lib = os.environ.get("OHOS_NATIVE_LLVM_LIB", "").strip()
        if llvm_lib and os.path.isdir(llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)

        with env.vars(self).apply():
            # 1. produce the .3d input
            self.run(f'"{os.path.join(build_dir, "test_sample3d")}" "{sample}"',
                     env="conanrun")
            # 2. run the packaged plotsauce binary on it (real end-to-end use)
            self.run(f'"{plotsauce_bin}" "{sample}" "{out}"', env="conanrun")
            # 3. validate the converted XML
            self.run(f'"{os.path.join(build_dir, "test_plotsauce")}" "{out}"',
                     env="conanrun")
