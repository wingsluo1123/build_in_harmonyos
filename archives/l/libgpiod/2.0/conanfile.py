#!/usr/bin/env python3
"""Conan recipe for libgpiod 2.0 — Linux GPIO device interaction library.

Builds the C library, C++ bindings, and command-line tools.
Uses autotools (configure + make).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgpiodConan(ConanFile):
    name = "libgpiod"
    version = "2.0"
    description = "Linux GPIO device interaction library"
    license = "LGPL-2.1"
    homepage = "https://git.kernel.org/pub/scm/libs/libgpiod/"

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
        # Enable tools and C++ bindings (no trimming per requirement)
        tc.configure_args.append("--enable-tools")
        tc.configure_args.append("--enable-bindings-cxx")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gpiod", "gpiodcxx"]
