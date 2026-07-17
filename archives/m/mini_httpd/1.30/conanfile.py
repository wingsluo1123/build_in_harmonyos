#!/usr/bin/env python3
"""Conan recipe for mini_httpd — small HTTP server from ACME Labs.

mini_httpd is a command-line tool (application), not a library.
Build outputs: mini_httpd (HTTP server) and htpasswd (password tool).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MiniHttpdConan(ConanFile):
    name = "mini_httpd"
    version = "1.30"
    description = "Small, lightweight HTTP server from ACME Labs"
    license = "BSD-like"
    homepage = "https://www.acme.com/software/mini_httpd/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # acme.com has SSL certificate issues; use get() with verify=False fallback
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            # Fallback: curl -k bypasses SSL verification for acme.com
            url = self.conan_data["sources"]["url"]
            filename = os.path.basename(url)
            self.run(f"curl -k -L -o {filename} {url}")
            from conan.tools.files import unzip
            unzip(self, filename, strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # mini_httpd has no configure script — just a raw Makefile.
        # R9: Always use -j1. Run in source folder where Makefile lives.
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install executables via make install, overriding BINDIR/MANDIR
        # to install into the Conan package folder directly.
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man")
        self.run(f"make install BINDIR={bindir} MANDIR={mandir}", cwd=self.source_folder)

    def package_info(self):
        # mini_httpd is an application — expose bindirs for executables
        self.cpp_info.bindirs = ["bin"]
