#!/usr/bin/env python3
"""Conan recipe for coturn 4.7.0-r0 (TURN/STUN server)."""

import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps


class CoturnConan(ConanFile):
    name = "coturn"
    version = "4.7.0-r0"
    package_type = "application"

    description = "Free open source implementation of TURN and STUN Server"
    license = "MIT"
    homepage = "https://github.com/coturn/coturn"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("libevent/2.1.12")
        self.requires("sqlite3/3.49.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-shared",
            "--enable-static",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        os.environ["TMPDIR"] = os.environ.get("TMPDIR", "/storage/Users/currentUser/tmp")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make("-j$(nproc)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []