#!/usr/bin/env python3
"""Conan recipe for cmatrix 2.0 — a scrolling Matrix like screen.

Build system: CMake.
This recipe uses the community fork abishekvashok/cmatrix (v2.0 tag)
because the official upstream bisqwit/cmatrix did not publish a v2.0 release.

Note: ncurses is used via system library (not a Conan dependency),
because ncurses is not yet published as a Conan package on the remote.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os


class CmatrixConan(ConanFile):
    name = "cmatrix"
    version = "2.0"
    description = "CMatrix — a scrolling Matrix like screen"
    license = "MIT"
    homepage = "https://github.com/abishekvashok/cmatrix"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Create ncurses.h wrapper if system ncurses only has curses.h
        curses_prefix = "/root/sysnc"
        if os.path.isdir(curses_prefix) and not os.path.isfile(os.path.join(curses_prefix, "include", "ncurses.h")):
            ncurses_h = os.path.join(self.source_folder, "ncurses.h")
            with open(ncurses_h, "w") as f:
                f.write('#include <curses.h>\n')
            self.output.info("Created ncurses.h wrapper in source folder")

    def generate(self):
        tc = CMakeToolchain(self)
        # Use system ncurses
        curses_prefix = "/root/sysnc"
        if os.path.isdir(curses_prefix):
            tc.variables["CMAKE_INCLUDE_PATH"] = f"{curses_prefix}/include"
            tc.variables["CMAKE_LIBRARY_PATH"] = f"{curses_prefix}/lib"
        # CMake >= 3.5 removed compatibility with cmake_minimum_required(VERSION 2.8)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Add source dir to include path for ncurses.h wrapper
        tc.variables["CMAKE_C_STANDARD_INCLUDE_DIRECTORIES"] = "${CMAKE_CURRENT_SOURCE_DIR}"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # CMakeLists.txt install target has issues with CMake 4.x relink dir
        # Manually copy the built binary
        build_dir = self.build_folder
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "cmatrix", src=build_dir, dst=bindir)

    def package_info(self):
        self.cpp_info.libs = ["cmatrix"]