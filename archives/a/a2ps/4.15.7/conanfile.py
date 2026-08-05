#!/usr/bin/env python3
"""Conan recipe for GNU a2ps 4.15.7 — Any to PostScript filter.

a2ps is a command-line tool that converts text files to PostScript.
It depends on bdw-gc (garbage collector) and libpaper (paper size library).

This recipe handles OHOS (HarmonyOS) platform adaptation including:
- config.guess/config.sub patches for OHOS platform detection
- umask fix for HarmonyOS filesystem compatibility
- LDFLAGS for unimplemented pthread syscalls
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class A2psConan(ConanFile):
    name = "a2ps"
    version = "4.15.7"
    description = "GNU a2ps - Any to PostScript filter"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/a2ps/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bdw-gc/8.2.6@ohpcd/stable")
        self.requires("libpaper/1.1.28@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Static build by default
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # Generate .pc files for pkg-config dependencies
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

        # Additional environment for OHOS platform compatibility
        env = Environment()
        env.append("LDFLAGS", "-Wl,--allow-shlib-undefined")
        env.append("AUTOMAKE", "true")
        env.append("ACLOCAL", "true")
        env.append("AUTOCONF", "true")
        env.append("AUTOHEADER", "true")
        env.append("MAKEINFO", "true")
        env.vars(self).save_script("a2ps_ohos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # a2ps is a command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
