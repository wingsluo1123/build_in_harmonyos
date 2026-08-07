#!/usr/bin/env python3
"""Conan recipe — List::MoreUtils::XS Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources (XS.xs) into a shared
library (XS.so) loaded by Perl's XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- Config::AutoConf::LMU cannot correctly detect types on OpenHarmony
  (compiler check programs fail due to -fstack-protector-strong issues).
  Patch 0001 skips all compiler checks and directly writes LMUconfig.h
  with the required HAVE_SIZE_T, HAVE_SSIZE_T, etc. macros.
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlListMoreUtilsXSConan(ConanFile):
    name = "perl-list-moreutils-xs"
    version = "0.430-r6"
    description = "Provide the stuff missing in List::Util in XS (high-performance Perl list utilities)"
    license = "Apache-2.0"
    homepage = "https://metacpan.org/dist/List-MoreUtils-XS"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies — uses system perl and system libc
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        # The patch skips Config::AutoConf::LMU checks and writes LMUconfig.h directly
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Build — compiles XS.xs (C code) into XS.so
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts from blib/ to package folder
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        # .so goes to lib/auto/List/MoreUtils/XS/ (Perl auto load path)
        copy(self, "XS.so",
             src=os.path.join(blib_arch, "auto", "List", "MoreUtils", "XS"),
             dst=os.path.join(self.package_folder, "lib", "auto", "List", "MoreUtils", "XS"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "List", "MoreUtils", "XS"),
             dst=os.path.join(self.package_folder, "lib", "auto", "List", "MoreUtils", "XS"))

        # .pm goes to lib/List/MoreUtils/ (Perl module path)
        copy(self, "XS.pm",
             src=os.path.join(blib_lib, "List", "MoreUtils"),
             dst=os.path.join(self.package_folder, "lib", "List", "MoreUtils"))

    def package_info(self):
        # This is a Perl XS module, not a C library.
        # The .so is loaded by Perl's XSLoader at runtime.
        # Set up the Perl library path for consumers.
        perl_lib = os.path.join(self.package_folder, "lib")
        self.output.info(f"Perl library path: {perl_lib}")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        # No cpp_info.libs — this is not a linkable C library
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
