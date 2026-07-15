#!/usr/bin/env python3
"""Conan recipe — nsnake 3.0.1 (ncurses snake game).

nsnake is a classic snake game on the terminal using ncurses. Upstream uses
a plain Makefile (not autotools). OHOS CI workers ship the ncurses runtime
library but NOT the development headers, so the ncurses headers and a matching
static libncurses.a are bundled under res/ (same approach as nudoku / bitwise).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NsnakeConan(ConanFile):
    name = "nsnake"
    version = "3.0.1"
    description = "nsnake - classic snake game on the terminal using ncurses"
    license = "GPL-3.0"
    homepage = "https://github.com/alexdantas/nSnake"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Bundle ncurses headers + static lib (res/) — CI workers ship the
        # ncurses runtime but lack the dev headers/static archive.
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def requirements(self):
        # ncurses is a system runtime library; headers/lib are bundled
        # because CI workers lack the dev package.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Copy bundled ncurses headers/lib from the export folder into the
        # source folder so build() can reach them.
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")
        cxx = ce.get("cpp", "clang++")

        src = self.source_folder
        out = self.build_folder

        # Bundled ncurses (CI workers lack dev headers). Create a symlink
        # ncurses.h -> curses.h since nsnake uses <ncurses.h>.
        bundled_inc = os.path.join(src, "res", "headers")
        bundled_lib = os.path.join(src, "res", "libs")
        if not os.path.isdir(bundled_inc):
            raise RuntimeError(f"bundled ncurses headers missing: {bundled_inc}")

        ncurses_h = os.path.join(bundled_inc, "ncurses.h")
        if not os.path.exists(ncurses_h):
            curses_h = os.path.join(bundled_inc, "curses.h")
            if os.path.exists(curses_h):
                # Create a redirect header if ncurses.h doesn't exist
                with open(ncurses_h, "w") as f:
                    f.write('#include <curses.h>\n')

        cxxflags = f"-O2 -Wall -Wextra -I{bundled_inc}"
        ldflags = f"-L{bundled_lib} -lncurses"

        # Build with the Makefile
        self.run(
            f"make -C {src} clean", ignore_errors=True
        )
        self.run(
            f"make -C {src} -j1 V=1 CC={cc} CXX={cxx} "
            f"CXXFLAGS='{cxxflags}' "
            f"CFLAGS_PLATFORM='-I{bundled_inc}' "
            f"LDFLAGS_PLATFORM='-L{bundled_lib} -lncurses' "
            f"PREFIX=/usr"
        )

    def package(self):
        copy(self, "nsnake",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]