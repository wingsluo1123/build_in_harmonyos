#!/usr/bin/env python3
"""Conan recipe — Crypt::OpenSSL::Bignum Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code that links against OpenSSL
libcrypto. The .so is loaded by Perl's XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- OPENSSL_PREFIX set to system OpenSSL installation path
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlcryptopensslbignumConan(ConanFile):
    name = "perl-crypt-openssl-bignum"
    version = "0.09-r13"
    description = "OpenSSL's multiprecision integer arithmetic (Perl XS module)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Crypt-OpenSSL-Bignum"
    url = ""  # CI fills this

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # OpenSSL (libcrypto) is a system-level dependency, not a Conan package
        # The Makefile.PL finds it via OPENSSL_PREFIX or pkg-config
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_openssl_prefix(self):
        """Resolve OpenSSL installation prefix without hardcoding user paths.

        Tries in order:
        1. pkg-config --variable=prefix openssl
        2. Derive from openssl binary location in PATH
        3. Common system paths /usr, /usr/local
        4. Raises ConanException if nothing found
        """
        import shutil
        import subprocess

        # 1. Try pkg-config
        try:
            result = subprocess.run(
                ["pkg-config", "--variable=prefix", "openssl"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                prefix = result.stdout.strip()
                if os.path.isfile(os.path.join(prefix, "include", "openssl", "ssl.h")):
                    return prefix
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # 2. Derive from openssl binary location in PATH
        openssl_bin = shutil.which("openssl")
        if openssl_bin:
            # e.g. /usr/local/bin/openssl -> /usr/local
            prefix = os.path.dirname(os.path.dirname(openssl_bin))
            if os.path.isfile(os.path.join(prefix, "include", "openssl", "ssl.h")):
                return prefix

        # 3. Try common system paths
        for candidate in ("/usr", "/usr/local"):
            if os.path.isfile(os.path.join(candidate, "include", "openssl", "ssl.h")):
                return candidate

        raise ConanException(
            "Cannot find OpenSSL prefix. Please set OPENSSL_PREFIX environment variable "
            "to the OpenSSL installation directory (e.g. /usr/local)."
        )

    def generate(self):
        # Set OPENSSL_PREFIX so Makefile.PL can find OpenSSL headers and libs
        openssl_prefix = os.environ.get("OPENSSL_PREFIX") or self._resolve_openssl_prefix()
        # Set in OS env so self.run() in build() picks it up (Makefile.PL reads env directly)
        os.environ["OPENSSL_PREFIX"] = openssl_prefix
        self.buildenv_info.define("OPENSSL_PREFIX", openssl_prefix)
        self.buildenv_info.append_path("LD_LIBRARY_PATH", os.path.join(openssl_prefix, "lib"))

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts from blib to package folder in standard layout
        # .so goes to lib/auto/Crypt/OpenSSL/Bignum/ (Perl auto path)
        # .pm goes to lib/Crypt/OpenSSL/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "Bignum.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Bignum"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "Bignum"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Bignum"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "Bignum"))
        copy(self, "Bignum.pm",
             src=os.path.join(blib_lib, "Crypt", "OpenSSL"),
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL"))
        copy(self, "CTX.pm",
             src=os.path.join(blib_lib, "Crypt", "OpenSSL", "Bignum"),
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL", "Bignum"))

    def package_info(self):
        # The shared library is Bignum.so (Perl XS extension)
        self.cpp_info.libs = ["Bignum"]
        self.cpp_info.libdirs = ["lib/auto/Crypt/OpenSSL/Bignum"]
        self.cpp_info.includedirs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
