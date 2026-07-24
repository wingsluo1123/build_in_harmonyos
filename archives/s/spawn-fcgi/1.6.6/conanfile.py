#!/usr/bin/env python3
"""Conan recipe — spawn-fcgi 1.6.6 (Meson, CLI tool)

spawn-fcgi is a simple program to spawn FastCGI processes.
It supports IPv4/IPv6 TCP sockets and Unix domain sockets.
No external dependencies — only uses libc functions.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SpawnFcgiConan(ConanFile):
    name = "spawn-fcgi"
    version = "1.6.6"
    description = "Simple program to spawn FastCGI processes"
    license = "BSD-3-Clause"
    homepage = "https://www.lighttpd.net/"

    package_type = "application"

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
        tc = MesonToolchain(self)
        tc.generate()
        # Inject ar into meson native file (profile doesn't set tools.build:archiver)
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file) as f:
            content = f.read()
        old_content = content
        content = content.replace(
            "[binaries]\nc =",
            "[binaries]\nar = '/data/service/hnp/bin/llvm-ar'\nc =",
        )
        if content == old_content:
            raise RuntimeError("Failed to inject ar into meson native file")
        with open(native_file, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
