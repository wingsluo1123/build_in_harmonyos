#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Spek, spek, 0.8.5, spek 0.8.5, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpekConan(ConanFile):
    name = "spek"
    version = "0.8.5"
    description = "Spek - Acoustic spectrum analyser (headless CLI build)"
    license = "GPL-3.0"
    homepage = "https://www.spek.cc/"
    url = "https://github.com/alexkay/spek"  # CI fills this

    package_type = "application"

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
        # Headless build: skip wxWidgets GUI
        tc.configure_args.append("--disable-gui")
        # R26: System-name libraries default to static
        if not self.options.shared:
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
        self.cpp_info.libs = ["spek"]

