#!/usr/bin/env python3
"""Conan recipe for fmt (modern C++ formatting library) on HarmonyOS PC (aarch64).

Upstream: https://github.com/fmtlib/fmt
Version 11.2.0-r1 = upstream 11.2.0 + first adaptation for HarmonyOS PC.
fmt is a header + compiled library providing fast, type-safe C++ formatting.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FmtConan(ConanFile):
    name = "fmt"
    version = "11.2.0-r1"
    description = "A modern formatting library for C++ (fast, type-safe, alternative to C stdio and iostreams)"
    license = "MIT"
    homepage = "https://github.com/fmtlib/fmt"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["FMT_DOC"] = "OFF"
        tc.variables["FMT_TEST"] = "OFF"
        tc.generate()

        # Fix compiler path: CI profile may point to a path that doesn't
        # exist on the local build machine. Detect and replace with the
        # system-resolved compiler from PATH.
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain_file):
            with open(toolchain_file, "r") as f:
                content = f.read()
            replaced = False
            clang_path = shutil.which("clang")
            clangxx_path = shutil.which("clang++")
            if clang_path and "/data/service/hnp/bin/clang" in content:
                content = content.replace("/data/service/hnp/bin/clang", clang_path)
                replaced = True
            if clangxx_path and "/data/service/hnp/bin/clang++" in content:
                content = content.replace("/data/service/hnp/bin/clang++", clangxx_path)
                replaced = True
            if replaced:
                with open(toolchain_file, "w") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["fmt"]
