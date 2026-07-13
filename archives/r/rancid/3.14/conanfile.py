#!/usr/bin/env python3
"""Conan recipe — rancid 3.14 (Autotools).

rancid is a network device configuration diff tool.
Most of its components are Perl/expect scripts; only hpuifilter and par
are compiled C binaries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RancidConan(ConanFile):
    name = "rancid"
    version = "3.14"
    description = "Really Awesome New Cisco confIg Differ - network device configuration management tool"
    license = "BSD-3-Clause"
    homepage = "https://www.shrubbery.net/rancid/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")
        # In-source build: rancid Makefiles don't use $(srcdir) for all files
        self.folders.build = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # rancid is a tool package — executables only, no shared libraries
        self.cpp_info.libs = []
        self.cpp_info.bindeps = []
