#!/usr/bin/env python3
"""Conan recipe — Crypt::OpenSSL::Verify Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code that links against OpenSSL
libssl/libcrypto. The .so is loaded by Perl's XSLoader/DynaLoader at runtime.

Dependencies:
  - OpenSSL (libssl, libcrypto) — system pre-installed, found via OPENSSL_PREFIX
  - Crypt::OpenSSL::Guess — bypassed by patch (0001-ohos-bypass-guess.patch)
  - Crypt::OpenSSL::X509 — runtime Perl dependency

Adaptations for OHOS:
- Patch bypasses Crypt::OpenSSL::Guess, uses OPENSSL_PREFIX env var
- R26: Verify.so is a Perl XS extension, not a system same-name library
- R27: OpenSSL is system-level dependency, not a Conan package (pass)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlcryptopensslverifyConan(ConanFile):
    name = "perl-crypt-openssl-verify"
    version = "0.36-r2"
    description = "OpenSSL X509 certificate verification (Perl XS module)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Crypt-OpenSSL-Verify"
    url = ""  # CI fills this

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # R27: OpenSSL (libssl/libcrypto) is a system-level dependency, not a Conan package
        # The Makefile.PL finds it via OPENSSL_PREFIX environment variable
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autotools/cmake toolchain needed — Perl Makefile.PL handles everything
        pass

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Set OPENSSL_PREFIX so Makefile.PL can find OpenSSL headers and libs
        openssl_prefix = os.environ.get("OPENSSL_PREFIX", "/storage/Users/currentUser/usr/local")
        old_env = {}
        for key in ("OPENSSL_PREFIX", "LD_LIBRARY_PATH"):
            old_env[key] = os.environ.get(key, "")
        os.environ["OPENSSL_PREFIX"] = openssl_prefix
        os.environ["LD_LIBRARY_PATH"] = (
            os.path.join(openssl_prefix, "lib") + ":" + old_env.get("LD_LIBRARY_PATH", "")
        )

        try:
            # Step 1: Generate Makefile using ExtUtils::MakeMaker
            self.run('perl Makefile.PL', cwd=self.source_folder)

            # Step 2: Build (R9: use -j1)
            self.run("make -j1", cwd=self.source_folder)
        finally:
            # Restore environment
            for key, val in old_env.items():
                if val:
                    os.environ[key] = val
                elif key in os.environ:
                    del os.environ[key]

    def package(self):
        # Copy built artifacts from blib to package folder in standard layout
        # .so goes to lib/auto/Crypt/OpenSSL/Verify/ (Perl auto path)
        # .pm goes to lib/Crypt/OpenSSL/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "Verify.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Verify"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "Verify"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Verify"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "Verify"))
        copy(self, "Verify.pm",
             src=os.path.join(blib_lib, "Crypt", "OpenSSL"),
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL"))

    def package_info(self):
        # The shared library is Verify.so (Perl XS extension)
        self.cpp_info.libs = ["Verify"]
        self.cpp_info.libdirs = ["lib/auto/Crypt/OpenSSL/Verify"]
        self.cpp_info.includedirs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
