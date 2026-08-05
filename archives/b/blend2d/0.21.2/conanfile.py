#!/usr/bin/env python3
"""Conan recipe for Blend2D 0.21.2 — High-performance 2D vector graphics engine.

Blend2D includes asmjit as a bundled dependency in the source release tarball,
so no external Conan dependencies are required.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Blend2DConan(ConanFile):
    name = "blend2d"
    version = "0.21.2"
    description = "High-performance 2D vector graphics engine with JIT compiler"
    license = "Zlib"
    homepage = "https://github.com/blend2d/blend2d"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("graphics", "2d", "vector", "rendering", "jit")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # asmjit is bundled in the source release tarball — no external dependency
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # blend2d uses BLEND2D_STATIC (not BUILD_SHARED_LIBS) to control library type
        tc.variables["BLEND2D_STATIC"] = "ON" if not self.options.shared else "OFF"
        tc.variables["BLEND2D_TEST"] = "OFF"
        tc.variables["BLEND2D_NO_INSTALL"] = "OFF"
        tc.variables["BLEND2D_NO_JIT"] = "OFF"
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
        self.cpp_info.libs = ["blend2d"]
