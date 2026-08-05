#!/usr/bin/env python3
"""Conan recipe for mini-httpd 1.3 (upstream archive: mini_httpd-1.30).
Application package: produces mini_httpd and htpasswd executables."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MinihttpdConan(ConanFile):
    name = "mini-httpd"
    version = "1.3"
    description = "Small HTTP server with SSL support"
    license = "GPL-2.0-or-later"
    homepage = "https://acme.com/software/mini_httpd/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # mini_httpd is a raw Makefile project with no configure script.
        # Build both mini_httpd and htpasswd executables.
        # CRYPT_LIB=-lcrypt is needed for htpasswd, provided by libc on OHOS.
        # CC=clang: OHOS SDK uses clang, not gcc.
        # R9: Use -j1, not -j$(nproc)
        # R33: Use explicit CC=clang instead of conf key (not available in all envs)
        self.run("make CC=clang -j1")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)

        copy(self, "mini_httpd", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "htpasswd", src=self.source_folder, dst=bindir, keep_path=False)

        # LICENSE is at the top of each source file (BSD-style), no standalone COPYRIGHT
        # file in the archive. Include README for attribution.
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]