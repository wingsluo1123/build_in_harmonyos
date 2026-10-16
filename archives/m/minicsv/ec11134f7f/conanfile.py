#!/usr/bin/env python3
"""Conan recipe for minicsv ec11134f7f.

MiniCSV is a tiny, fast, single-file, BSD-licensed CSV parsing library in C
(no heap allocations; handles multi-line and escaped rows).  Upstream ships
only minicsv.c / minicsv.h / minicsv-test.c with no build system, so this
recipe provides a minimal CMakeLists.txt that builds the static library and
installs the header — the same pattern as the MurmurHash3 recipe in this repo.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class MinicsvConan(ConanFile):
    name = "minicsv"
    version = "ec11134f7f"
    description = "MiniCSV — a tiny, fast, simple, single-file CSV parsing library in C"
    license = "ISC"
    homepage = "https://github.com/jedisct1/minicsv"
    url = "https://github.com/jedisct1/minicsv"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # No upstream build system; use the classic single-folder layout so the
        # injected CMakeLists.txt resolves sources relative to the source dir.
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Static library only — no RUNTIME component, so no bin/ install
        # (keeps L0k/R38 satisfied: library package needs no commands.json).
        cmake_content = """cmake_minimum_required(VERSION 3.15)
project(minicsv C)
add_library(minicsv minicsv.c)
target_include_directories(minicsv PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
install(TARGETS minicsv
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib)
install(FILES minicsv.h DESTINATION include)
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["minicsv"]