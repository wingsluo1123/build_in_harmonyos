#!/usr/bin/env python3
"""Conan recipe — bc (arbitrary precision calculator language).

bc is a command-line calculator tool, not a library.
This recipe enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BcConan(ConanFile):
    name = "bc"
    version = "1.07.1"
    description = "Arbitrary precision calculator language"
    license = "MIT"
    homepage = "https://www.gnu.org/software/bc/"
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
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: Fix HMDFS umask 077 permission issue in configure/config.status
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")
        # Skip documentation (makeinfo not available on OHOS)
        os.environ["MAKEINFO"] = "true"
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "MAKEINFO=true", "SUBDIRS=lib bc"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["SUBDIRS=lib bc"])

    def package_info(self):
        self.cpp_info.libs = []
