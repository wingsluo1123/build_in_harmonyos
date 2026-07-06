#!/usr/bin/env python3
"""Conan recipe for perl-crypt-openssl-x509 2.0.1-r1.

Crypt::OpenSSL::X509 — Perl extension to OpenSSL's X509 API.
Build system: Perl ExtUtils::MakeMaker (Makefile.PL).
Produces: X509.so (Perl XS shared object) + X509.pm

Dependencies:
  - OpenSSL (libssl, libcrypto) — system pre-installed
  - Crypt::OpenSSL::Guess (Perl module) — configure-time
  - Convert::ASN1 (Perl module) — runtime

R26: This module links against system OpenSSL (libssl.so/libcrypto.so).
     The output X509.so is a Perl XS extension, not a system same-name library.
     No system lib path pollution risk.
R32: settings.os check uses `in ("Linux", "OHOS")`.

Platform limitation (E073): On OpenHarmony, HMDFS user directories have SELinux
context u:object_r:hmdfs:s0 which prevents dlopen() of .so files at runtime.
The .so must be installed to a system directory (e.g. /data/service/hnp/) with
context u:object_r:hnp_file:s0 for runtime loading to work.
LD_PRELOAD can load the .so at process startup, but OHOS dlsym(RTLD_DEFAULT)
does not search LD_PRELOAD libraries (unlike Linux glibc).
See reports/test-report.md for full platform compatibility analysis.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlCryptOpensslX509Conan(ConanFile):
    name = "perl-crypt-openssl-x509"
    version = "2.0.1-r1"
    description = "Perl extension to OpenSSL's X509 API"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://github.com/dsully/perl-crypt-openssl-x509"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # OpenSSL prefix — auto-detect from env var or common paths
    @property
    def _openssl_prefix(self):
        """OpenSSL prefix: try OPENSSL_PREFIX env var, then common paths."""
        # 1. Explicit env var
        prefix = os.environ.get("OPENSSL_PREFIX")
        if prefix and os.path.isfile(os.path.join(prefix, "include", "openssl", "asn1.h")):
            return prefix
        # 2. User-installed (cmd-pkgs default: $HOME/usr/local)
        home = os.path.expanduser("~")
        for candidate in [
            os.path.join(home, "usr", "local"),
            "/usr/local",
            "/usr",
            "/data/service/hnp",
        ]:
            if os.path.isfile(os.path.join(candidate, "include", "openssl", "asn1.h")):
                return candidate
        # 3. Fallback to env var or /usr/local
        return prefix or "/usr/local"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL is system pre-installed; declared as system_libs in package_info
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
        prefix = self._openssl_prefix
        os.environ["OPENSSL_PREFIX"] = prefix
        # Compiler include/library paths for OpenSSL headers
        inc_dir = os.path.join(prefix, "include")
        lib_dir = os.path.join(prefix, "lib")
        cflags = os.environ.get("CFLAGS", "")
        os.environ["CFLAGS"] = f"-I{inc_dir} {cflags}" if cflags else f"-I{inc_dir}"
        ldflags = os.environ.get("LDFLAGS", "")
        os.environ["LDFLAGS"] = f"-L{lib_dir} {ldflags}" if ldflags else f"-L{lib_dir}"
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{ld}" if ld else lib_dir
        _home = os.path.expanduser("~")
        p5 = os.environ.get("PERL5LIB", "")
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
            raise Exception(f"Unsupported OS: {self.settings.os}")

        self._setup_env()

        # Step 1: Configure (perl Makefile.PL) — pass INC/LIBS explicitly
        # to ensure compiler finds OpenSSL headers even if Guess module fails
        prefix = self._openssl_prefix
        inc = f"-I{prefix}/include"
        libs = f"-L{prefix}/lib -lssl -lcrypto"
        self.run(
            f'perl Makefile.PL INC="{inc}" LIBS="{libs}"',
            cwd=self.source_folder,
        )

        # Step 2: Build
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
        x509_so = os.path.join(self.source_folder, "blib", "arch", "auto", "Crypt", "OpenSSL", "X509", "X509.so")
        x509_pm = os.path.join(self.source_folder, "blib", "lib", "Crypt", "OpenSSL", "X509.pm")

        if not os.path.exists(os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Crypt", "OpenSSL", "X509", "X509.so")):
            if os.path.exists(x509_so):
                dst = os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Crypt", "OpenSSL", "X509", "X509.so")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(x509_so, dst)

        if not os.path.exists(os.path.join(self.package_folder, "lib", "perl5", "Crypt", "OpenSSL", "X509.pm")):
            if os.path.exists(x509_pm):
                dst = os.path.join(self.package_folder, "lib", "perl5", "Crypt", "OpenSSL", "X509.pm")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(x509_pm, dst)

    def package_info(self):
        self.cpp_info.libs = ["X509"]
        # R32: System libraries declared via system_libs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["ssl", "crypto"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
