#!/usr/bin/env python3
"""Conan recipe — lmod 9.2.5 (Autotools)"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LmodConan(ConanFile):
    name = "lmod"
    version = "9.2.5"
    description = "Lua-based environment module system for dynamically managing user environment"
    license = "MIT"
    homepage = "https://github.com/TACC/Lmod"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Point lmod to the Lua installation from the Conan dependency
        lua_prefix = self.dependencies["lua"].package_folder
        tc.configure_args.append(f"--with-lua={lua_prefix}")
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
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define("LMOD_PKG", self.package_folder)
        self.runenv_info.define("LMOD_DIR", os.path.join(self.package_folder, "lmod", self.version))
