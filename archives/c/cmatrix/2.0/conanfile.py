#!/usr/bin/env python3
"""Conan recipe for cmatrix 2.0 — a scrolling Matrix like screen.

Build system: CMake.
This recipe uses the community fork abishekvashok/cmatrix (v2.0 tag)
because the official upstream bisqwit/cmatrix did not publish a v2.0 release.

Note: ncurses is used via system library (not a Conan dependency),
because ncurses is not yet published as a Conan package on the remote.
The CMakeLists.txt is patched to use check_library_exists() instead of
find_package(Curses) for OHOS/HarmonyOS compatibility.
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
        # Create ncurses.h wrapper: OHOS system ncurses typically provides
        # only curses.h, not ncurses.h. This wrapper lets cmatrix.c find
        # <ncurses.h> while actually using curses.h underneath.
        ncurses_h = os.path.join(self.source_folder, "ncurses.h")
        if not os.path.isfile(ncurses_h):
            with open(ncurses_h, "w") as f:
                f.write('#include <curses.h>\n')
            self.output.info("Created ncurses.h wrapper in source folder")
        # Patch CMakeLists.txt: replace find_package(Curses) with direct linking
        # because find_package(Curses) is incompatible with OHOS/HarmonyOS in CMake 4.x
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.isfile(cmake_lists):
            with open(cmake_lists, "r") as f:
                content = f.read()
            old_block = "Set(CURSES_NEED_NCURSES TRUE)\nfind_package(Curses)\ninclude_directories(${CURSES_INCLUDE_DIR})\nadd_definitions(-DHAVE_NCURSES_H)"
            new_block = "# Direct linking with ncurses (find_package incompatible with OHOS/CMake 4.x)\nset(CURSES_LIBRARIES \"ncurses\")\nadd_definitions(-DHAVE_NCURSES_H)"
            if old_block in content:
                content = content.replace(old_block, new_block)
                with open(cmake_lists, "w") as f:
                    f.write(content)
                self.output.info("Patched CMakeLists.txt: replaced find_package(Curses) with direct linking")
            else:
                self.output.warning("Could not find find_package(Curses) block in CMakeLists.txt - may already be patched")

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 3.5 removed compatibility with cmake_minimum_required(VERSION 2.8)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Add source dir to include path for ncurses.h wrapper
        tc.variables["CMAKE_C_STANDARD_INCLUDE_DIRECTORIES"] = "${CMAKE_CURRENT_SOURCE_DIR}"
        # Search for ncurses in common OHOS/system paths
        for prefix in ["/root/sysnc", "/storage/Users/currentUser/usr/local", "/system", "/usr"]:
            libpath = os.path.join(prefix, "lib64")
            if os.path.isdir(libpath) and os.path.exists(os.path.join(libpath, "libncurses.a")):
                tc.variables["CMAKE_LIBRARY_PATH"] = libpath
                self.output.info(f"Found ncurses at {libpath}")
                break
            libpath = os.path.join(prefix, "lib")
            if os.path.isdir(libpath) and os.path.exists(os.path.join(libpath, "libncurses.a")):
                tc.variables["CMAKE_LIBRARY_PATH"] = libpath
                self.output.info(f"Found ncurses at {libpath}")
                break
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Create ncurses.h wrapper in the build folder (source folder may be cached)
        # OHOS system ncurses typically provides only curses.h, not ncurses.h
        build_ncurses_h = os.path.join(self.source_folder, "ncurses.h")
        if not os.path.isfile(build_ncurses_h):
            with open(build_ncurses_h, "w") as f:
                f.write('#include <curses.h>\n')
            self.output.info("Created ncurses.h wrapper in source folder")
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