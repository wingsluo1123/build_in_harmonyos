#!/usr/bin/env python3
"""Conan recipe — libogg 1.3.6 (Autotools).

R26: libogg is a system-name-colliding library — build static only
     to avoid polluting /lib, /lib64 with a shared libogg.so.
E165: HarmonyOS shebang fix — /bin/sh not accessible, use /data/app/bin/bash
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LiboggConan(ConanFile):
    name = "libogg"
    version = "1.3.6"
    description = "Ogg multimedia container library"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/ogg/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name-colliding library — static only
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebang for HarmonyOS — /bin/sh not accessible
        _configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(_configure):
            replace_in_file(self, _configure, "#! /bin/sh", "#! /data/app/bin/bash")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ogg"]
        self.cpp_info.set_property("cmake_file_name", "libogg")
        self.cpp_info.set_property("cmake_target_name", "libogg::libogg")
