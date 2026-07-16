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
    exports_sources = "compat/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Curses headers use different layouts across OHOS build workers.
        # Upstream requires <ncurses.h>, so provide a portable dispatcher and
        # fall back to the generated ncurses 6.4 headers when CI has only the
        # static library installed.
        ncurses_h = os.path.join(self.source_folder, "ncurses.h")
        if not os.path.isfile(ncurses_h):
            with open(ncurses_h, "w", encoding="utf-8") as f:
                f.write(
                    "#if __has_include(<curses.h>)\n"
                    "#  include <curses.h>\n"
                    "#elif __has_include(<ncurses/curses.h>)\n"
                    "#  include <ncurses/curses.h>\n"
                    "#elif __has_include(<ncursesw/curses.h>)\n"
                    "#  include <ncursesw/curses.h>\n"
                    "#else\n"
                    "#  include \"compat/curses.h\"\n"
                    "#endif\n"
                )
            self.output.info("Created portable ncurses.h wrapper")

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 3.5 removed compatibility with cmake_minimum_required(VERSION 2.8)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Add source dir for the ncurses.h wrapper. CI publishes system
        # dependencies under /storage/.../usr/local; the local builder keeps
        # its ncurses staging tree under /root/sysnc.
        include_dirs = [self.source_folder, os.path.join(self.source_folder, "compat")]
        library_dirs = []
        for prefix in ("/storage/Users/currentUser/usr/local", "/root/sysnc"):
            include_dir = os.path.join(prefix, "include")
            library_dir = os.path.join(prefix, "lib")
            if os.path.isdir(include_dir):
                include_dirs.append(include_dir)
            if os.path.isdir(library_dir):
                library_dirs.append(library_dir)
        tc.variables["CMAKE_C_STANDARD_INCLUDE_DIRECTORIES"] = ";".join(include_dirs)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(library_dirs)
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
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