#!/usr/bin/env python3
"""Conan recipe for igraph 1.0.0 — CMake-based network analysis library."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


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

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["IGRAPH_USE_INTERNAL_ARPACK"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_BLAS"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_LAPACK"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_GLPK"] = "ON"
        tc.variables["IGRAPH_USE_INTERNAL_GMP"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.libs = ["igraph"]
        self.cpp_info.set_property("pkg_config_name", "igraph")