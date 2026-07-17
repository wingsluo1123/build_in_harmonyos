#!/usr/bin/env python3
"""Conan recipe for cmatrix 2.0 — a scrolling Matrix like screen.

Build system: CMake.
This recipe uses the community fork abishekvashok/cmatrix (v2.0 tag)
because the official upstream bisqwit/cmatrix did not publish a v2.0 release.

Note: ncurses is built from the bundled official 6.4 source archive because
it is not yet published as a Conan package on the remote and CI workers do not
consistently provide its development files.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os
import shutil
import tarfile


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

    def _build_ncurses(self):
        archive = os.path.join(self.source_folder, "compat", "ncurses-6.4.tar.gz")
        ncurses_src = os.path.join(self.build_folder, "ncurses-src")
        ncurses_prefix = os.path.join(self.build_folder, "ncurses")
        os.makedirs(ncurses_src, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tf:
            for member in tf.getmembers():
                parts = member.name.split("/", 1)
                if len(parts) != 2 or not parts[1]:
                    continue
                member.name = parts[1]
                tf.extract(member, ncurses_src, filter="data")
        self.run(
            f'cd "{ncurses_src}" && '
            'CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/ar '
            'ARFLAGS=rcs RANLIB=/data/service/hnp/bin/ranlib ./configure '
            f'--prefix="{ncurses_prefix}" --without-shared --without-debug '
            '--without-ada --without-cxx --without-cxx-binding --without-manpages '
            '--without-progs --without-tests --disable-db-install --enable-widec'
        )
        self.run(
            f'cd "{ncurses_src}" && '
            'for f in ncurses/Makefile panel/Makefile menu/Makefile form/Makefile; do '
            'test ! -f "$f" || sed -i "s/^ARFLAGS[[:space:]]*=.*/ARFLAGS = rcs/" "$f"; '
            'done && make -j1 libs'
        )
        lib_dir = os.path.join(ncurses_prefix, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy2(os.path.join(ncurses_src, "lib", "libncursesw.a"), lib_dir)

    def build(self):
        self._build_ncurses()
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