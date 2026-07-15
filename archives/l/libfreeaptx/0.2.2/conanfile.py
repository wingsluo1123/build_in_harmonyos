#!/usr/bin/env python3
"""Conan recipe for libfreeaptx — aptX/aptX HD audio codec library.

libfreeaptx is a free implementation of the Audio Processing Technology
codec (aptX), derived from ffmpeg 4.0 and licensed under LGPLv2.1+.
It provides a shared library (libfreeaptx.so) and command-line
utilities (freeaptxenc, freeaptxdec) for aptX/aptX HD encoding/decoding.

Build system: POSIX Makefile (no configure step).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibfreeaptxConan(ConanFile):
    name = "libfreeaptx"
    version = "0.2.2"
    description = "Free implementation of Audio Processing Technology codec (aptX)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/regularhunter/libfreeaptx"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Raw Makefile build — no configure step needed.
        # The Makefile uses $(CC) which defaults to cc (=clang on OHOS).
        # R9: Always use -j1.
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install using the Makefile's install target with PREFIX pointing
        # to the Conan package folder. This handles symlinks, pkgconfig, etc.
        self.run(f"make install PREFIX={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["freeaptx"]
        self.cpp_info.bindirs = ["lib", "bin"]
        self.cpp_info.set_property("pkg_config_name", "libfreeaptx")
