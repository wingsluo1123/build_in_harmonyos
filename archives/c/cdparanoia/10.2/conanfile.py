#!/usr/bin/env python3
"""Conan recipe for cdparanoia 10.2 — CD audio extraction library and tool.

Build system: autotools (configure + make)
Products: libcdda_interface, libcdda_paranoia (libraries) + cdparanoia (CLI tool)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdparanoiaConan(ConanFile):
    name = "cdparanoia"
    version = "10.2"
    description = "CD audio extraction library and tool with error correction"
    license = "GPL-2.0"
    homepage = "https://xiph.org/paranoia/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cdparanoia")
        self.cpp_info.set_property("cmake_target_name", "cdparanoia::cdparanoia")
        self.cpp_info.libs = ["cdda_interface", "cdda_paranoia"]
        self.cpp_info.system_libs = ["rt", "m"]
