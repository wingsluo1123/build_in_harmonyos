#!/usr/bin/env python3
"""Conan recipe for libieee1284 — IEEE 1284 parallel port communication library.

Build system: autotools (configure + make)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libieee1284Conan(ConanFile):
    name = "libieee1284"
    version = "0.2.11"
    description = "Library for interfacing IEEE 1284-compatible devices (parallel port)"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/libieee1284/"
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
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable python bindings (not needed for C library)
        tc.configure_args.append("--without-python")
        tc.generate()
        # E002: Ensure TMPDIR is set (HarmonyOS /tmp is read-only)
        if not os.environ.get("TMPDIR"):
            os.environ["TMPDIR"] = os.path.join(os.path.expanduser("~"), "tmp")
            os.makedirs(os.environ["TMPDIR"], exist_ok=True)

    def build(self):
        apply_conandata_patches(self)
        # E011: Fix umask 077→022 for HMDFS permission compatibility
        # configure is a generated file excluded from patch system, fix at build time
        self.run("sed -i 's/umask 077/umask 022/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ieee1284"]
