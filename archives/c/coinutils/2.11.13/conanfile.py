#!/usr/bin/env python3
"""Conan recipe — COIN-OR CoinUtils (autotools build).

COIN-OR utilities: base utility library for the COIN-OR project.
Provides data structures (vectors, matrices), file I/O (MPS, LP format),
message handling, and other utilities used by COIN-OR solvers.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CoinutilsConan(ConanFile):
    name = "coinutils"
    version = "2.11.13"
    description = "COIN-OR utilities (COIN-OR project base utility library)"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/CoinUtils"
    url = ""  # CI fills this

    package_type = "library"

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
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Override compiler/shell paths: profile may point to paths that
        # don't exist on all machines. Append overrides to conanbuild.sh
        # so they take effect when sourced.
        bash_path = shutil.which("bash") or "/bin/sh"
        clang = shutil.which("clang") or "clang"
        clangxx = shutil.which("clang++") or "clang++"
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        conanbuild = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.exists(conanbuild):
            with open(conanbuild, "a") as f:
                f.write(f'\nexport CC="{clang}"\n')
                f.write(f'\nexport CXX="{clangxx}"\n')
                f.write(f'\nexport SHELL="{bash_path}"\n')
                f.write(f'\nexport CONFIG_SHELL="{bash_path}"\n')
                f.write(f'\nexport TMPDIR="{tmpdir}"\n')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["CoinUtils"]
        self.cpp_info.includedirs = ["include/coin"]
