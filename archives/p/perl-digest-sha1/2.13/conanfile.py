#!/usr/bin/env python3
"""Conan recipe — Digest::SHA1 Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources (SHA1.xs) into a shared
library loaded by Perl's XSLoader/DynaLoader.

On OHOS with Perl 5.42.0, the build works without any patches — the system
Perl is properly configured with clang and correct include/lib paths.

R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlDigestSHA1Conan(ConanFile):
    name = "perl-digest-sha1"
    version = "2.13"
    description = "Perl interface to the SHA-1 algorithm"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/Digest::SHA1"
    # url is filled by CI from conandata.yml source URL

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Use absolute INSTALL_BASE pointing to staging dir in build folder
        install_base = os.path.join(self.build_folder, "lib", "perl5")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')

        # Step 2: Build
        self.run("make -j1")

        # Step 3: Install to staging dir (no DESTDIR needed — INSTALL_BASE is absolute)
        self.run("make install")

    def package(self):
        # Copy installed files from build staging to package folder
        copy(self, "*.so", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # This is a Perl XS module, not a C library
        # The .so is loaded by Perl's XSLoader at runtime
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        # MakeMaker installs modules under lib/perl5/$arch/ (e.g. aarch64-linux)
        arch_dirs = glob.glob(os.path.join(perl_lib, "*"))
        for d in arch_dirs:
            if os.path.isdir(d):
                self.runenv_info.append_path("PERL5LIB", d)
                self.output.info(f"PERL5LIB arch path: {d}")
                break
