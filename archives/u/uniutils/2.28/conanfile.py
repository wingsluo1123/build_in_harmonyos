#!/usr/bin/env python3
"""Conan recipe - uniutils 2.28 (Autotools command-line utilities)."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UniutilsConan(ConanFile):
    name = "uniutils"
    version = "2.28"
    description = "Utilities for manipulating and examining UTF-8 and Unicode data"
    license = "GPL-3.0-or-later"
    homepage = "https://billposer.org/Software/uniutils.html"
    url = "https://billposer.org/Software/Downloads/uniutils-2.28.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The bundled configure script cannot bootstrap Automake depfiles on
        # OHOS. Dependency tracking is optional; disabling it keeps the
        # normal configure/make/install path intact.
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS may drop the executable bit when configure copies install-sh.
        os.chmod(os.path.join(self.source_folder, "install-sh"), 0o755)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
