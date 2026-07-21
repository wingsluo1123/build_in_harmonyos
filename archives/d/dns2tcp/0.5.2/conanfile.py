#!/usr/bin/env python3
"""Conan recipe — dns2tcp 0.5.2 (Autotools)"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class Dns2TcpConan(ConanFile):
    name = "dns2tcp"
    version = "0.5.2"
    description = "Tool for relaying TCP connections over DNS (DNS tunnel)"
    license = "GPL-2.0"
    homepage = "https://www.hsc.fr/"

    package_type = "application"

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # dns2tcp's Makefile uses relative include paths requiring in-source build
        src = self.source_folder
        self.run(f"cd {src} && ./configure --prefix={self.package_folder}", env="conanbuild")
        self.run(f"cd {src} && make -j1", env="conanbuild")

    def package(self):
        self.run(f"cd {self.source_folder} && make install", env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
