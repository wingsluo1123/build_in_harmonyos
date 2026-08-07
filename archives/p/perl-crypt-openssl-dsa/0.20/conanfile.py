#!/usr/bin/env python3
"""Conan recipe for Crypt-OpenSSL-DSA 0.20 — Perl XS module for OpenSSL DSA.

Crypt::OpenSSL::DSA is a Perl XS module providing DSA (Digital Signature
Algorithm) key generation, signing, and verification using OpenSSL's libcrypto.
The build system is Perl's ExtUtils::MakeMaker (perl Makefile.PL → make).

Source: Downloaded from CPAN (official mirror).

Platform adaptations for HarmonyOS:
1. OpenSSL path: detected from ~/usr/local (installed via cmd-pkgs)
2. Makefile.PL natively supports OPENSSL_PREFIX env var for OpenSSL detection
3. No Crypt::OpenSSL::Guess dependency (unlike Crypt::OpenSSL::RSA)
4. No LDDLFLAGS patch needed (default linker flags work on OHOS)

R32: settings.os must check in ("Linux", "OHOS").
R33: No hardcoded absolute paths — all paths detected at build time.
"""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches,
    copy, get,
)
from conan.tools.layout import basic_layout


class CryptOpenSSLDSAConan(ConanFile):
    name = "perl-crypt-openssl-dsa"
    version = "0.20"
    description = "Perl XS module for OpenSSL DSA (Digital Signature Algorithm)"
    license = "perl_5"
    homepage = "https://metacpan.org/pod/Crypt::OpenSSL::DSA"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _detect_perl_info(self):
        try:
            perl_ver = subprocess.check_output(
                ["perl", "-e", 'print sprintf("%vd", $^V)'],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            perl_ver = "5.42.0"
        try:
            perl_arch = subprocess.check_output(
                ["perl", "-MConfig", "-e", "print $Config{archname}"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            perl_arch = "aarch64-linux"
        return perl_ver, perl_arch

    def _detect_openssl_paths(self):
        """Detect OpenSSL library and include paths, install if missing."""
        home = os.path.expanduser("~")
        openssl_lib = f"{home}/usr/local/lib"
        openssl_inc = f"{home}/usr/local/include"

        if not os.path.exists(f"{openssl_lib}/libcrypto.so") and not os.path.exists(f"{openssl_lib}/libcrypto.a"):
            self.run(
                'curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openssl 1.1.1w'
            )

        return openssl_lib, openssl_inc

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        openssl_lib, openssl_inc = self._detect_openssl_paths()
        perl_ver, perl_arch = self._detect_perl_info()

        env_prefix = f'LD_LIBRARY_PATH="{openssl_lib}" '

        # Makefile.PL natively supports OPENSSL_PREFIX and LIBS/INC parameters
        self.run(
            f'{env_prefix}perl Makefile.PL '
            f'LIBS="-L{openssl_lib} -lcrypto" '
            f'INC="-I{openssl_inc}"',
            cwd=src,
        )

        self.run(f'{env_prefix}make', cwd=src)

    def package(self):
        src = self.source_folder
        perl_ver, perl_arch = self._detect_perl_info()

        # Copy .so from blib/arch (architecture-dependent)
        so_src = os.path.join(src, "blib", "arch", "auto", "Crypt", "OpenSSL", "DSA")
        so_dst = os.path.join(self.package_folder, "lib", "site_perl", perl_ver, perl_arch, "auto", "Crypt", "OpenSSL", "DSA")
        copy(self, "*.so", so_src, so_dst)
        copy(self, "*.bs", so_src, so_dst)

        # Copy .pm and .pod from blib/lib (architecture-independent)
        pm_src = os.path.join(src, "blib", "lib", "Crypt", "OpenSSL")
        pm_dst = os.path.join(self.package_folder, "lib", "site_perl", perl_ver, "Crypt", "OpenSSL")
        copy(self, "DSA.pm", pm_src, pm_dst)
        copy(self, "*.pod", pm_src, pm_dst)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []

        # Set up PERL5LIB for consumers
        perl_ver, perl_arch = self._detect_perl_info()
        perl_lib = os.path.join(self.package_folder, "lib", "site_perl", perl_ver)
        arch_lib = os.path.join(perl_lib, perl_arch)
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.runenv_info.append_path("PERL5LIB", arch_lib)
        self.output.info(f"Perl library path: {perl_lib}")
        self.output.info(f"Perl arch library path: {arch_lib}")
