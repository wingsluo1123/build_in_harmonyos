#!/usr/bin/env python3
"""Conan recipe for Crypt::OpenSSL::VerifyX509 — a Perl XS module.

This module provides simple X.509 certificate verification using OpenSSL.
Build system: ExtUtils::MakeMaker (perl Makefile.PL + make).

Dependencies:
  - OpenSSL (libcrypto, libssl) — system library
  - Crypt::OpenSSL::X509 (Perl runtime dep) — Conan package @ohpcd/stable
  - Perl runtime (>= 5.008)

R26: VerifyX509.so is a Perl XS extension, not a system same-name library.
     No system lib path pollution risk.
R27: Crypt::OpenSSL::X509 declared as @ohpcd/stable Conan requirement.
R32: settings.os check uses `in ("Linux", "OHOS")`.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Perlcryptopensslverifyx509Conan(ConanFile):
    name = "perl-crypt-openssl-verifyx509"
    version = "0.21-r5"
    description = "Crypt::OpenSSL::VerifyX509 - simple certificate verification"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Crypt-OpenSSL-VerifyX509"
    url = "https://cpan.metacpan.org/authors/id/T/TI/TIMLEGGE/Crypt-OpenSSL-VerifyX509-0.21.tar.gz"

    settings = "os", "compiler", "build_type", "arch"

    @property
    def _openssl_prefix(self):
        """OpenSSL prefix from OPENSSL_PREFIX env var, default to ~/usr/local."""
        return os.environ.get("OPENSSL_PREFIX", os.path.join(os.path.expanduser("~"), "usr", "local"))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # R27: Crypt::OpenSSL::X509 runtime dependency declared as @ohpcd/stable
        self.requires("perl-crypt-openssl-x509/2.0.1-r1@ohpcd/stable")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self.buildenv_info.define("OPENSSL_PREFIX", self._openssl_prefix)
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", f"{self._openssl_prefix}/lib")
        self.buildenv_info.define("CC", "clang")
        self.buildenv_info.define("CXX", "clang++")

        # Add X509 dependency's Perl lib paths to PERL5LIB
        x509 = self.dependencies.get("perl-crypt-openssl-x509")
        if x509 and x509.package_folder:
            self.buildenv_info.prepend_path("PERL5LIB",
                os.path.join(x509.package_folder, "lib", "perl5", "aarch64-linux"))
            self.buildenv_info.prepend_path("PERL5LIB",
                os.path.join(x509.package_folder, "lib", "perl5"))

        # System Perl lib paths for other deps (Crypt::OpenSSL::Guess, Convert::ASN1)
        _home = os.path.expanduser("~")
        self.buildenv_info.prepend_path("PERL5LIB", f"{_home}/usr/local/lib/perl5/aarch64-linux")
        self.buildenv_info.prepend_path("PERL5LIB", f"{_home}/usr/local/lib/perl5")

    def _setup_env(self):
        """Set up environment variables directly in os.environ for subprocess."""
        os.environ["OPENSSL_PREFIX"] = self._openssl_prefix
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{self._openssl_prefix}/lib:{ld}" if ld else f"{self._openssl_prefix}/lib"

        _home = os.path.expanduser("~")
        paths = [
            f"{_home}/usr/local/lib/perl5/aarch64-linux",
            f"{_home}/usr/local/lib/perl5",
        ]

        # Add X509 dependency's Perl lib paths
        x509 = self.dependencies.get("perl-crypt-openssl-x509")
        if x509 and x509.package_folder:
            paths.insert(0, os.path.join(x509.package_folder, "lib", "perl5", "aarch64-linux"))
            paths.insert(0, os.path.join(x509.package_folder, "lib", "perl5"))

        p5 = os.environ.get("PERL5LIB", "")
        if p5:
            paths.append(p5)
        os.environ["PERL5LIB"] = ":".join(paths)
        os.environ["CC"] = "clang"
        os.environ["CXX"] = "clang++"

    def build(self):
        apply_conandata_patches(self)

        # R32: Platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        self._setup_env()

        # Step 1: Generate Makefile (perl Makefile.PL)
        # R1: parameter minimalization — INSTALL_BASE=/ for clean lib/ layout
        self.run("perl Makefile.PL INSTALL_BASE=/", cwd=self.source_folder)

        # Step 2: Build the XS extension
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self._setup_env()

        # Install using DESTDIR (INSTALL_BASE already set in Makefile)
        self.run(
            f"make install DESTDIR={self.package_folder}",
            cwd=self.source_folder,
        )

        # Fallback: copy from blib if make install didn't place files correctly
        so_src = os.path.join(self.source_folder, "blib", "arch", "auto", "Crypt", "OpenSSL", "VerifyX509", "VerifyX509.so")
        pm_src = os.path.join(self.source_folder, "blib", "lib", "Crypt", "OpenSSL", "VerifyX509.pm")

        so_dst = os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Crypt", "OpenSSL", "VerifyX509", "VerifyX509.so")
        pm_dst = os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "Crypt", "OpenSSL", "VerifyX509.pm")

        if not os.path.exists(so_dst) and os.path.exists(so_src):
            os.makedirs(os.path.dirname(so_dst), exist_ok=True)
            shutil.copy2(so_src, so_dst)

        if not os.path.exists(pm_dst) and os.path.exists(pm_src):
            os.makedirs(os.path.dirname(pm_dst), exist_ok=True)
            shutil.copy2(pm_src, pm_dst)

    def package_info(self):
        # VerifyX509.so is a Perl XS shared object, not a traditional C library
        self.cpp_info.libs = ["VerifyX509"]
        self.cpp_info.libdirs = ["lib"]
        # R32: System libraries declared via system_libs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["crypto", "ssl"]
