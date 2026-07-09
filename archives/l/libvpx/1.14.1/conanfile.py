#!/usr/bin/env python3
"""Conan recipe for libvpx 1.14.1 — Makefile project.

libvpx is a VP8/VP9 codec SDK.
"""

import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibvpxConan(ConanFile):
    name = "libvpx"
    version = "1.14.1"
    description = "VP8/VP9 Codec SDK"
    license = "BSD-3-Clause"
    homepage = "https://www.webmproject.org/code/"
    url = "https://chromium.googlesource.com/webm/libvpx"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # libvpx uses configure + make
        bash_path = shutil.which("bash") or "bash"
        self.run(f"{bash_path} configure --target=aarch64-linux-gcc --disable-examples --disable-tools --disable-unit-tests --disable-docs --enable-vp9 --enable-vp8 --prefix={self.package_folder}")
        self.run(f"make -j{self.settings.get('cpu_count', 2)} SHELL={bash_path}")

    def package(self):
        self.run("make install")
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["vpx"]
        self.cpp_info.includedirs = ["include"]