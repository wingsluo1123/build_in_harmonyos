#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libao, libao, 1.2.2, libao 1.2.2, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibaoConan(ConanFile):
    name = "libao"
    version = "1.2.2"
    description = "libao 1.2.2"
    license = "MIT"
    homepage = ""
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
        # Static build per task requirements
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Generate configure script (source only has configure.ac)
        self.run("autoreconf -ivf", cwd=self.source_folder)
        # E165: Fix shebangs for OpenHarmony
        self.run("sed -i '1s|#!/bin/sh|#!/system/bin/sh|' configure install-sh compile depcomp missing 2>/dev/null; true", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ao"]
