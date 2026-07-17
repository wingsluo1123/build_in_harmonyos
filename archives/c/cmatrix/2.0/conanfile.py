#!/usr/bin/env python3
"""Conan recipe for cmatrix 2.0 — a scrolling Matrix like screen.

Build system: CMake.
This recipe uses the community fork abishekvashok/cmatrix (v2.0 tag)
because the official upstream bisqwit/cmatrix did not publish a v2.0 release.

Note: ncurses is bundled as a verified OHOS static archive because it is not
published as a Conan package on the remote and CI workers do not consistently
provide writable local build storage or development files.
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
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_C_STANDARD_INCLUDE_DIRECTORIES"] = ";".join(
            [self.source_folder, os.path.join(self.source_folder, "compat")]
        )
        tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(self.build_folder, "ncurses", "lib")
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
        tc.generate()

    def _prepare_ncurses(self):
        lib_dir = os.path.join(self.build_folder, "ncurses", "lib")
        os.makedirs(lib_dir, exist_ok=True)
        copy(
            self,
            "libncurses.a",
            src=os.path.join(self.source_folder, "compat"),
            dst=lib_dir,
        )

    def build(self):
        self._prepare_ncurses()
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