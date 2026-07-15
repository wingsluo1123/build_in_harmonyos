#!/usr/bin/env python3
"""Conan recipe for farbfeld — suckless lossless image format with conversion tools.

farbfeld is a set of command-line tools for converting between farbfeld format
and PNG/JPEG/PPM/PAM. It uses a plain Makefile build system.

Dependencies: libpng (for png2ff/ff2png), libjpeg (for jpg2ff/ff2jpg)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FarbfeldConan(ConanFile):
    name = "farbfeld"
    version = "4.0.0"
    description = "Suckless lossless image format with 16-bit RGBA pixel data and conversion tools"
    license = "ISC"
    homepage = "https://tools.suckless.org/farbfeld/"
    url = "https://dl.suckless.org/farbfeld/farbfeld-4.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, NEVER from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = compilers.get("c", "clang") if isinstance(compilers, dict) else "clang"

        # Gather dependency include and lib paths
        inc_dirs = []
        lib_dirs = []
        for dep_name in ["libpng", "libjpeg"]:
            dep = self.dependencies.get(dep_name)
            if dep:
                try:
                    agg = dep.cpp_info.aggregated_components
                    if callable(agg):
                        agg = agg()
                    inc_dirs.extend(agg.includedirs)
                    lib_dirs.extend(agg.libdirs)
                except Exception:
                    inc_dirs.extend(dep.cpp_info.includedirs)
                    lib_dirs.extend(dep.cpp_info.libdirs)

        cppflags = "-D_DEFAULT_SOURCE " + " ".join(f"-I{d}" for d in inc_dirs)
        cflags = "-std=c99 -pedantic -Wall -Wextra -Os -fPIC"
        ldflags = " ".join(f"-L{d}" for d in lib_dirs)

        # R9: Always use -j1
        self.run(
            f"make CC={cc} "
            f"CPPFLAGS='{cppflags}' "
            f"CFLAGS='{cflags}' "
            f"LDFLAGS='{ldflags}' "
            f"PNG-LDLIBS='-lpng -lz' "
            f"JPG-LDLIBS='-ljpeg' "
            f"-j1",
            cwd=self.source_folder
        )

    def package(self):
        # Copy built binaries to bin/ (binaries are in source_folder where make ran)
        for binary in ["png2ff", "ff2png", "jpg2ff", "ff2jpg", "ff2pam", "ff2ppm", "2ff"]:
            copy(self, binary, self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
