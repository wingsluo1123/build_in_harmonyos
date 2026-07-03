#!/usr/bin/env python3
"""Conan recipe — Crypt::OpenSSL::AES Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code that links against OpenSSL
libcrypto. The .so is loaded by Perl's XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- CCFLAGS patched with -isystem <sysroot> for system headers
- LDDLFLAGS patched with -nostartfiles -nodefaultlibs -lc (missing crti.o/crtn.o)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlcryptopensslaesConan(ConanFile):
    name = "perl-crypt-openssl-aes"
    version = "0.21-r1"
    description = "A Perl wrapper around OpenSSL's AES library (Perl XS module)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Crypt-OpenSSL-AES"
    url = ""  # CI fills this

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # OpenSSL (libcrypto) is a system-level dependency, not a Conan package
        # in the ohpcd channel. The Makefile.PL finds it via OPENSSL_PREFIX
        # or INC/LIBS parameters. See generate() for OPENSSL_PREFIX setup.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set OPENSSL_PREFIX so Makefile.PL can find OpenSSL headers and libs
        home = os.environ.get("HOME", os.path.expanduser("~"))
        openssl_prefix = os.environ.get("OPENSSL_PREFIX", os.path.join(home, "usr", "local"))
        self.buildenv_info.define("OPENSSL_PREFIX", openssl_prefix)
        self.buildenv_info.append_path("LD_LIBRARY_PATH", os.path.join(openssl_prefix, "lib"))

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        home = os.environ.get("HOME", os.path.expanduser("~"))
        prefix = os.path.join(home, "usr", "local")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run(
            f'perl Makefile.PL PREFIX={prefix} '
            f'INC="-I{prefix}/include" '
            f'LIBS="-L{prefix}/lib -lcrypto"',
            cwd=self.source_folder,
        )

        # Step 2: Patch Makefile for OpenHarmony platform
        #   a) Add sysroot include path for system headers (sys/types.h etc.)
        #   b) Add CRT workaround: -nostartfiles -nodefaultlibs -lc
        makefile_path = os.path.join(self.source_folder, "Makefile")
        with open(makefile_path, "r") as f:
            content = f.read()

        sysroot_inc = os.environ.get(
            "OHOS_SYSROOT_INC",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include"
        )
        content = re.sub(
            r"^(CCFLAGS = -D_GNU_SOURCE)",
            rf"CCFLAGS = -isystem {sysroot_inc} -D_GNU_SOURCE",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^LDDLFLAGS = -shared -O2 -fstack-protector-strong$",
            "LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc -O2 -fstack-protector-strong",
            content,
            flags=re.MULTILINE,
        )

        with open(makefile_path, "w") as f:
            f.write(content)

        # Step 3: Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts from blib to package folder in standard layout
        # .so goes to lib/auto/Crypt/OpenSSL/AES/ (Perl auto path)
        # .pm goes to lib/Crypt/OpenSSL/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "AES.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "AES"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "AES"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "AES"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "AES"))
        copy(self, "AES.pm",
             src=os.path.join(blib_lib, "Crypt", "OpenSSL"),
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL"))

        # Also copy .so to lib/ root for CI script .so discovery (L5/R26 check)
        copy(self, "AES.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "AES"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # The shared library is AES.so (Perl XS extension)
        self.cpp_info.libs = ["AES"]
        self.cpp_info.libdirs = ["lib/auto/Crypt/OpenSSL/AES"]
        self.cpp_info.includedirs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
