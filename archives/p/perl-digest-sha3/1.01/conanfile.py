#!/usr/bin/env python3
"""Conan recipe — Digest::SHA3 Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources (src/sha3.c, src/sdf.c)
into a shared library (.so) loaded by Perl's XSLoader/DynaLoader.

Adaptations for OHOS:
- Perl's Config already provides -D_GNU_SOURCE and proper lib paths
- No source patches needed — Makefile.PL works as-is
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlDigestSHA3Conan(ConanFile):
    name = "perl-digest-sha3"
    version = "1.01"
    description = "Perl extension for SHA-3 (NIST FIPS 202 SHA-3 and SHAKE algorithms)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Digest-SHA3"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
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
        copy(self, "*.xs", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        # Include the sha3sum script if installed
        copy(self, "sha3sum", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # This is a Perl XS module, not a C library
        # The .so is loaded by Perl's XSLoader at runtime
        # Set up the Perl library path for consumers
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        # MakeMaker installs modules under lib/perl5/$arch/ (e.g. aarch64-linux)
        # Find the arch-specific directory dynamically
        arch_dirs = glob.glob(os.path.join(perl_lib, "*"))
        for d in arch_dirs:
            if os.path.isdir(d):
                self.runenv_info.append_path("PERL5LIB", d)
                self.output.info(f"PERL5LIB arch path: {d}")
                break
        # No cpp_info.libs — this is not a linkable C library
