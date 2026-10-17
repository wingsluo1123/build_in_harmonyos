#!/usr/bin/env python3
"""Conan recipe for edid-decode 20220315 (linuxtv snapshot, plain Makefile)."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class EdidDecodeConan(ConanFile):
    name = "edid-decode"
    version = "20220315"
    package_type = "application"
    description = "EDID block decoder and display metadata parser (linuxtv edid-decode)."
    license = "MIT"
    homepage = "https://git.linuxtv.org/edid-decode.git/"
    url = "https://git.linuxtv.org/edid-decode.git/"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # Upstream only builds in-tree (single-shot `$(CXX) ... -o edid-decode`).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cxx", "clang++") if compilers else "clang++"
        # The upstream Makefile already consumes $(CXX) $(CPPFLAGS) $(CFLAGS)
        # $(LDFLAGS) and adds -lm itself; there is no configure step.
        self.run("make -j1 CXX={}".format(cxx))

    def package(self):
        # OpenHarmony images ship no /usr/bin/install(1) (`command -v install`
        # is empty on the device), so the upstream `make install` target cannot
        # run here. Copy the two artifacts into the standard package layout.
        copy(
            self,
            "edid-decode",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "edid-decode.1",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
