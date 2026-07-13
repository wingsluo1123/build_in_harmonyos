#!/usr/bin/env python3
"""Conan test_package for wasm-micro-runtime — L1 test.

Verifies that libiwasm.a can be linked and the WAMR runtime API
(wasm_runtime_init/destroy) is functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WasmMicroRuntimeTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_wasm")
        self.run(bin_path, env="conanrun")
