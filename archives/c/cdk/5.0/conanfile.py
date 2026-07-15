#!/usr/bin/env python3
"""Conan recipe - cdk 5.0 (Curses Development Kit, Autotools).

CDK is a library of predefined curses widgets for terminal applications.
This recipe builds the static libcdk.

R26: Static linking for system-name libraries.
E007: config.guess/config.sub patched for HarmonyOS platform support.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdkConan(ConanFile):
    name = "cdk"
    version = "5.0"
    description = "Curses Development Kit - a library of widgets for curses terminal apps"
    license = "BSD-4-Clause-UC"
    homepage = "https://dickey.his.com/cdk/cdk.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        # OHOS platform: force static, remove shared option (R26)
        if self.settings.os == "OHOS":
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: static by default for system-name libraries
        if not self.options.get_safe("shared"):
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
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
        self.cpp_info.libs = ["cdk"]
