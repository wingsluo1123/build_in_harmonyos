#!/usr/bin/env python3
"""Conan recipe for wasm-micro-runtime (WAMR) 2.4.4.

WAMR is a lightweight, standalone WebAssembly runtime by Bytecode Alliance.
Build produces static library libiwasm.a with interpreter, AOT, WASI support.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class WasmMicroRuntimeConan(ConanFile):
    name = "wasm-micro-runtime"
    version = "2.4.4"
    description = "WebAssembly Micro Runtime (WAMR) - a lightweight, standalone WebAssembly runtime"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/bytecodealliance/wasm-micro-runtime"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["WAMR_BUILD_PLATFORM"] = "linux"
        tc.variables["WAMR_BUILD_TARGET"] = "AARCH64"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        simde_dir = os.environ.get("SIMDE_SOURCE_DIR", "")
        if simde_dir and os.path.isdir(simde_dir):
            tc.variables["FETCHCONTENT_SOURCE_DIR_SIMDE"] = simde_dir
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["iwasm"]
