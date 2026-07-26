#!/usr/bin/env python3
"""Conan recipe for igraph 1.0.0 — CMake-based network analysis library."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save
import os


class IgraphConan(ConanFile):
    name = "igraph"
    version = "1.0.0"
    description = "Library for the analysis of networks"
    license = "MIT"
    homepage = "https://igraph.org"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "patches/arith.h", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["IGRAPH_VERSION"] = "1.0.0"
        # Respect the user's `shared` option instead of hardcoding OFF.
        # CMakeToolchain already sets CMAKE_SYSTEM_NAME from Conan settings.os,
        # so OHOS platform modules load correctly — do not override to "Linux".
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["IGRAPH_USE_INTERNAL_ARPACK"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_BLAS"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_LAPACK"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_GLPK"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_GMP"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["F2C_EXTERNAL_ARITH_HEADER"] = os.path.join(self.source_folder, "patches", "arith.h")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # arith.h is a direct header replacement (not a unified-diff patch),
        # so apply_conandata_patches won't copy it. Inject it into the source
        # tree so F2C_EXTERNAL_ARITH_HEADER resolves. export_sources() placed
        # it under export_sources_folder/patches/; copy from there to the
        # source_folder so the build-time path is correct.
        os.makedirs(os.path.join(self.source_folder, "patches"), exist_ok=True)
        copy(
            self,
            "arith.h",
            src=os.path.join(self.export_sources_folder, "patches"),
            dst=os.path.join(self.source_folder, "patches"),
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["igraph"]
        self.cpp_info.set_property("pkg_config_name", "igraph")