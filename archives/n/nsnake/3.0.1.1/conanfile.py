#!/usr/bin/env python3
"""Conan recipe for nsnake, a terminal snake game."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NsnakeConan(ConanFile):
    name = "nsnake"
    version = "3.0.1.1"
    description = "Classic snake game on the terminal using ncurses"
    license = "GPL-3.0"
    homepage = "https://github.com/alexdantas/nSnake"
    url = "https://github.com/alexdantas/nSnake"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        cxx = executables.get("cpp", "clang++")
        dep = self.dependencies["ncurses"]
        include_dirs = dep.cpp_info.includedirs or [os.path.join(dep.package_folder, "include")]
        lib_dirs = dep.cpp_info.libdirs or [os.path.join(dep.package_folder, "lib")]
        libraries = dep.cpp_info.libs or ["ncursesw"]
        include_flags = " ".join(f"-I{path}" for path in include_dirs)
        link_flags = " ".join(f"-l{name}" for name in libraries)
        self.run(f"make -C {self.source_folder} clean", ignore_errors=True)
        self.run(
            f"make -C {self.source_folder} -j1 V=1 CC={cc} CXX={cxx} "
            f"CXXFLAGS='-O2 -Wall -Wextra {include_flags}' "
            f"CFLAGS_PLATFORM='{include_flags}' "
            f"LDFLAGS='-L{lib_dirs[0]} {link_flags}'"
        )

    def package(self):
        copy(self, "nsnake", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
