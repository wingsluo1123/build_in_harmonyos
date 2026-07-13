#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libcsv, libcsv, 3.0.3, libcsv 3.0.3, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcsvConan(ConanFile):
    name = "libcsv"
    version = "3.0.3"
    description = "Fast and flexible CSV library written in pure ANSI C"
    license = "LGPL-2.1"
    homepage = "https://github.com/rgamble/libcsv"
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
        # R26: Static linking - build only static library
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Fix config.guess/config.sub for HarmonyOS platform
        candidates = glob.glob("/usr/local/share/automake-*/config.guess") + \
                     glob.glob("/storage/Users/currentUser/usr/local/share/automake-*/config.guess")
        if candidates:
            am_dir = os.path.dirname(candidates[0])
            copy(self, "config.guess", am_dir, src)
            copy(self, "config.sub", am_dir, src)
        # Fix umask 077 issue on HMDFS (0700 dirs cannot be written to)
        configure_path = os.path.join(src, "configure")
        replace_in_file(self, configure_path, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["csv"]
