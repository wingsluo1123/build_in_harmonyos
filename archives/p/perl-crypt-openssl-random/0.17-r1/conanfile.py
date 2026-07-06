#!/usr/bin/env python3
"""Conan recipe — Crypt::OpenSSL::Random Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code that links against OpenSSL
libcrypto. The .so is loaded by Perl's XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- OPENSSL_PREFIX set to system OpenSSL installation path
- R27: perl-crypt-openssl-guess dependency uses @ohpcd/stable
- R32: settings.os check uses `in ("Linux", "OHOS")`
- R26: Not applicable (Perl XS .so is not a system same-name library)
- OHOS library name fix: system OpenSSL libs are named libssloh.so.3 /
  libcryptooh.so.3 (not libssl.so.3 / libcrypto.so.3). patchelf is used
  in package() to fix NEEDED entries and set RPATH to the system lib dir.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlcryptopensslrandomConan(ConanFile):
    name = "perl-crypt-openssl-random"
    version = "0.17-r1"
    description = "OpenSSL/LibreSSL pseudo-random number generation (Perl XS module)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Crypt-OpenSSL-Random"
    url = ""  # CI fills this

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # R27: Crypt::OpenSSL::Guess is needed by Makefile.PL to locate OpenSSL
        self.requires("perl-crypt-openssl-guess/0.15-r1@ohpcd/stable")

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
        os.environ["OPENSSL_PREFIX"] = openssl_prefix
        self.buildenv_info.define("OPENSSL_PREFIX", openssl_prefix)
        self.buildenv_info.append_path("LD_LIBRARY_PATH", os.path.join(openssl_prefix, "lib"))

        # Set CC=clang for Perl's MakeMaker (E001: cc not found on OHOS)
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        self.buildenv_info.define("CC", cc)
        self.buildenv_info.define("CXX", cxx)

        # Set PERL5LIB to include Crypt::OpenSSL::Guess from the dependency
        guess_dep = self.dependencies["perl-crypt-openssl-guess"]
        guess_pkg = guess_dep.package_folder
        # The .pm is at lib/perl5/Crypt/OpenSSL/Guess.pm
        perl5_lib = os.path.join(guess_pkg, "lib", "perl5")
        if os.path.isdir(perl5_lib):
            os.environ["PERL5LIB"] = perl5_lib + os.pathsep + os.environ.get("PERL5LIB", "")
            self.buildenv_info.append_path("PERL5LIB", perl5_lib)

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Build
        self.run("make -j1", cwd=self.source_folder)

    def _fix_ohos_lib_names(self, so_path):
        """Fix NEEDED entries for OHOS platform.

        OHOS ships OpenSSL as libssloh.so.3 / libcryptooh.so.3 (with "oh"
        suffix), but the build links against libssl.so.3 / libcrypto.so.3
        from the user-installed OpenSSL. Use patchelf to fix NEEDED entries
        and set RPATH to the system library directory.
        """
        import shutil

        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        if not os.path.isfile(patchelf):
            self.output.warning("patchelf not found, skipping OHOS lib name fix")
            return

        # Resolve system OpenSSL lib directory (where libssloh.so.3 lives)
        ssl_lib_dir = os.path.join(openssl_prefix, "lib") if "openssl_prefix" in dir(self) else None
        if not ssl_lib_dir or not os.path.isdir(ssl_lib_dir):
            # Fallback: search common system paths for libssloh.so.3
            for candidate in (
                "/data/service/hnp/python.org/python_3.12/lib",
                "/usr/lib",
                "/usr/local/lib",
            ):
                if os.path.isfile(os.path.join(candidate, "libssloh.so.3")):
                    ssl_lib_dir = candidate
                    break

        if not ssl_lib_dir:
            self.output.warning("Cannot find libssloh.so.3, skipping OHOS lib name fix")
            return

        self.output.info(f"Fixing OHOS lib names in {so_path}")
        self.run(f'{patchelf} --replace-needed libssl.so.3 libssloh.so.3 "{so_path}"')
        self.run(f'{patchelf} --replace-needed libcrypto.so.3 libcryptooh.so.3 "{so_path}"')
        self.run(f'{patchelf} --set-rpath {ssl_lib_dir} "{so_path}"')
        self.output.info(f"NEEDED fixed: libssl.so.3→libssloh.so.3, libcrypto.so.3→libcryptooh.so.3, RPATH={ssl_lib_dir}")

    def package(self):
        # Copy built artifacts from blib to package folder in standard layout
        # .so goes to lib/auto/Crypt/OpenSSL/Random/ (Perl auto path)
        # .pm goes to lib/Crypt/OpenSSL/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        so_dst = os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "Random")
        copy(self, "Random.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Random"),
             dst=so_dst)
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "Random"),
             dst=so_dst)
        copy(self, "Random.pm",
             src=os.path.join(blib_lib, "Crypt", "OpenSSL"),
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL"))

        # Fix OHOS library names in the packaged .so (E073/E166 adaptation)
        packaged_so = os.path.join(so_dst, "Random.so")
        if os.path.isfile(packaged_so):
            self._fix_ohos_lib_names(packaged_so)

    def package_info(self):
        # The shared library is Random.so (Perl XS extension)
        self.cpp_info.libs = ["Random"]
        self.cpp_info.libdirs = ["lib/auto/Crypt/OpenSSL/Random"]
        self.cpp_info.includedirs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
