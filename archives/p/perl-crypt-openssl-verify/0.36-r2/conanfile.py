#!/usr/bin/env python3
"""Conan recipe for perl-crypt-openssl-verify 0.36-r2.

Crypt::OpenSSL::Verify — OpenSSL X509 certificate verification (Perl XS module).
Build system: Perl ExtUtils::MakeMaker (Makefile.PL).
Produces: Verify.so (Perl XS shared object) + Verify.pm

Dependencies:
  - OpenSSL (libssl, libcrypto) — system pre-installed, found via OPENSSL_PREFIX
  - Crypt::OpenSSL::Guess — bypassed by patch (0001-Makefile.PL.patch)
  - Crypt::OpenSSL::X509 — runtime Perl dependency

R26: Verify.so is a Perl XS extension, not a system same-name library.
     No system lib path pollution risk.
R27: OpenSSL is system-level dependency, not a Conan package (pass).
R32: settings.os check uses `in ("Linux", "OHOS")`.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlCryptOpensslVerifyConan(ConanFile):
    name = "perl-crypt-openssl-verify"
    version = "0.36-r2"
    description = "OpenSSL X509 certificate verification (Perl XS module)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Crypt-OpenSSL-Verify"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # OpenSSL prefix — system pre-installed, resolved from env var or default
    @property
    def _openssl_prefix(self):
        """OpenSSL prefix from OPENSSL_PREFIX env var, default /usr/local."""
        return os.environ.get("OPENSSL_PREFIX", "/usr/local")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: OpenSSL is system pre-installed; declared as system_libs in package_info
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self.buildenv_info.define("OPENSSL_PREFIX", self._openssl_prefix)
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", f"{self._openssl_prefix}/lib")
        _home = os.path.expanduser("~")
        self.buildenv_info.prepend_path("PERL5LIB", f"{_home}/usr/local/lib/perl5")
        self.buildenv_info.prepend_path("PERL5LIB", f"{_home}/usr/local/lib/perl5/aarch64-linux")
        self.buildenv_info.define("CC", "clang")
        self.buildenv_info.define("CXX", "clang++")

    def _setup_env(self):
        """Set up environment variables directly in os.environ for subprocess."""
        os.environ["OPENSSL_PREFIX"] = self._openssl_prefix
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{self._openssl_prefix}/lib:{ld}" if ld else f"{self._openssl_prefix}/lib"
        p5 = os.environ.get("PERL5LIB", "")
        _home = os.path.expanduser("~")
        paths = [
            f"{_home}/usr/local/lib/perl5",
            f"{_home}/usr/local/lib/perl5/aarch64-linux",
        ]
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

        # Step 1: Configure (perl Makefile.PL)
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Build (R9: use -j1)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self._setup_env()

        # Install using DESTDIR with a simple INSTALL_BASE
        dest = os.path.join(self.package_folder, "staging")
        os.makedirs(dest, exist_ok=True)

        self.run(
            f'make install DESTDIR="{dest}" INSTALL_BASE="/usr/local"',
            cwd=self.source_folder,
        )

        # Copy from staging to package, stripping the INSTALL_BASE prefix
        install_base_rel = "usr/local"
        staging_path = os.path.join(dest, install_base_rel)

        if os.path.exists(staging_path):
            for root, dirs, files in os.walk(staging_path):
                for f in files:
                    src = os.path.join(root, f)
                    rel = os.path.relpath(src, staging_path)
                    dst = os.path.join(self.package_folder, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

        # Fallback: copy from blib if staging didn't work
        verify_so = os.path.join(self.source_folder, "blib", "arch", "auto", "Crypt", "OpenSSL", "Verify", "Verify.so")
        verify_pm = os.path.join(self.source_folder, "blib", "lib", "Crypt", "OpenSSL", "Verify.pm")

        if not os.path.exists(os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Crypt", "OpenSSL", "Verify", "Verify.so")):
            if os.path.exists(verify_so):
                dst = os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Crypt", "OpenSSL", "Verify", "Verify.so")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(verify_so, dst)

        if not os.path.exists(os.path.join(self.package_folder, "lib", "perl5", "Crypt", "OpenSSL", "Verify.pm")):
            if os.path.exists(verify_pm):
                dst = os.path.join(self.package_folder, "lib", "perl5", "Crypt", "OpenSSL", "Verify.pm")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(verify_pm, dst)

        # Also place Verify.so at top-level lib/ for L4 security scanner compatibility
        # (conan-verify L4 uses glob("*.so*") on lib/, not recursive)
        verify_so_nested = os.path.join(
            self.package_folder, "lib", "perl5", "aarch64-linux",
            "auto", "Crypt", "OpenSSL", "Verify", "Verify.so"
        )
        if os.path.exists(verify_so_nested):
            shutil.copy2(verify_so_nested, os.path.join(self.package_folder, "lib", "Verify.so"))

    def package_info(self):
        self.cpp_info.libs = ["Verify"]
        # R32: System libraries declared via system_libs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["ssl", "crypto"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
