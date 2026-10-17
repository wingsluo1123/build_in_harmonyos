#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libest, libest, 1.0.0, libest 1.0.0, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibestConan(ConanFile):
    name = "libest"
    version = "1.0.0"
    description = "libest 1.0.0"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")

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
        # libest configure.ac: --with-ssl-dir -> SSL_CFLAGS/LDFLAGS point at
        # $ssldir/include and $ssldir/lib; point it at the conan openssl
        # package folder so headers/libs resolve inside the dependency graph.
        tc.configure_args.append(
            "--with-ssl-dir=" + self.dependencies["openssl"].package_folder)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Build the library only (src/est). The example/ programs are demo
        # utilities, not part of the library deliverable; they contain
        # legacy OpenSSL 1.x-only code and are excluded from the package.
        autotools.make(args=["-j1", "-C", "src"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-C", "src", "-j1"])

    def package_info(self):
        self.cpp_info.libs = ["est"]
        # libest installs its public header under $(includedir)/est (see
        # src/est/Makefile.am: library_includedir=$(includedir)/est).
        self.cpp_info.includedirs = ["include/est"]
        self.cpp_info.requires = ["openssl::openssl"]
