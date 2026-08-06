#!/usr/bin/env python3
"""Conan recipe for mold 2.39.1 — a modern high-performance linker.

mold is a faster drop-in replacement for the Unix linker.
This recipe builds mold as an application (executable + wrapper library).
Uses bundled third-party deps (zlib, TBB, zstd, BLAKE3) to ensure
a self-contained binary that works on HarmonyOS without shared
library namespace issues (E088).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MoldConan(ConanFile):
    name = "mold"
    version = "2.39.1"
    description = "mold: A Modern Linker (LD replacement)"
    license = "MIT"
    homepage = "https://github.com/rui314/mold"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS, force Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Fix: conan sets CMAKE_INSTALL_LIBEXECDIR="bin" which conflicts
        # with mold's symlink install (bin/mold/ld vs bin/mold binary)
        tc.variables["CMAKE_INSTALL_LIBEXECDIR"] = "libexec"
        # Disable mimalloc: bundled mimalloc uses features not available on OHOS
        tc.variables["MOLD_USE_MIMALLOC"] = False
        # Use bundled TBB/zlib/zstd/BLAKE3 for self-contained binary
        # (avoids E088 musl namespace shared library resolution issues)
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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
