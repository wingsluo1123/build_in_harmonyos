#!/usr/bin/env python3
"""Conan recipe for THC Hydra 9.6."""

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HydraConan(ConanFile):
    name = "hydra"
    version = "9.6"
    description = "THC Hydra - fast network logon cracker supporting many protocols"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/vanhauser-thc/thc-hydra"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-xhydra", "--nostrip"])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
