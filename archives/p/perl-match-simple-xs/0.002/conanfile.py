#!/usr/bin/env python3
"""Conan recipe — match::simple::XS Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources (XS.xs) into a shared library
loaded by Perl's XSLoader/DynaLoader.

The XS module provides a C-accelerated backend for match::simple pattern matching.
No patches needed — builds cleanly on OHOS with system Perl 5.42.0.

R32: settings.os check uses `in ("Linux", "OHOS")`
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy


class PerlMatchSimpleXsConan(ConanFile):
    name = "perl-match-simple-xs"
    version = "0.002"
    package_type = "library"
    description = "XS backend for match::simple — high performance pattern matching in C"
    license = "perl_5"
    homepage = "https://metacpan.org/release/match-simple-XS"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autotools/cmake toolchain needed — Perl Makefile.PL handles everything
        pass

    def build(self):
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
        # Set up the Perl library path for consumers
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        # MakeMaker with INSTALL_BASE=X installs to X/lib/perl5/$arch/
        # Since INSTALL_BASE=build_folder/lib/perl5, the package has:
        #   package_folder/lib/perl5/lib/perl5/$arch/...
        # Find the arch-specific directory by locating auto/ subdir (XS marker)
        arch_dir = None
        for root, dirs, _ in os.walk(perl_lib):
            if "auto" in dirs:
                arch_dir = root
                break
        if arch_dir:
            self.runenv_info.append_path("PERL5LIB", arch_dir)
            self.output.info(f"PERL5LIB arch path: {arch_dir}")
        # No cpp_info.libs — this is not a linkable C library
