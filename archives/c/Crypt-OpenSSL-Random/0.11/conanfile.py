#!/usr/bin/env python3
"""Conan recipe for Crypt-OpenSSL-Random — Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
XS module: Random.xs → Random.c → Random.so (links against libssl/libcrypto)
Dependencies: OpenSSL (libssl, libcrypto)

Platform adaptation (OpenHarmony):
  1. CRT files missing: musl does not provide standard CRT startup files
     Fix: Add -nostartfiles -nodefaultlibs -lc to LDDLFLAGS
  2. OpenSSL paths: Explicitly pass INCDIR/LIBDIR from Conan dependency
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CryptOpensslRandomConan(ConanFile):
    name = "crypt-openssl-random"
    version = "0.11"
    description = "OpenSSL/LibreSSL pseudo-random number generator access"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/Crypt::OpenSSL::Random"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Get OpenSSL paths from Conan dependency
        dep = self.dependencies["openssl"]
        openssl_inc = dep.cpp_info.includedirs[0]
        openssl_lib = dep.cpp_info.libdirs[0]

        # Step 1: Generate Makefile via Makefile.PL with OpenSSL paths
        self.run(
            f"perl Makefile.PL INCDIR={openssl_inc} LIBDIR={openssl_lib}",
            cwd=self.source_folder,
        )

        # Step 2: Patch Makefile for OpenHarmony platform
        # R32: Platform guard — CRT fix is OHOS-specific (musl lacks CRT startup files)
        if self.settings.os == "OHOS":
            makefile_path = os.path.join(self.source_folder, "Makefile")
            with open(makefile_path, "r") as f:
                content = f.read()

            content = re.sub(
                r"^(LDDLFLAGS = -shared)",
                r"\1 -nostartfiles -nodefaultlibs -lc",
                content,
                flags=re.MULTILINE,
            )

            with open(makefile_path, "w") as f:
                f.write(content)

        # Step 3: Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts from blib/ to package folder
        # .so goes to lib/auto/Crypt/OpenSSL/Random/ (Perl auto path)
        # .pm goes to lib/Crypt/OpenSSL/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "Random.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Random"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "Random"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Random"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "Random"))
        copy(self, "Random.pm",
             src=os.path.join(blib_lib, "Crypt", "OpenSSL"),
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL"))

    def package_info(self):
        # Perl XS module — provides Random.so (shared library) + Random.pm (Perl module)
        self.cpp_info.libs = ["Random"]
        self.cpp_info.libdirs = ["lib/auto/Crypt/OpenSSL/Random"]
        self.cpp_info.includedirs = []


