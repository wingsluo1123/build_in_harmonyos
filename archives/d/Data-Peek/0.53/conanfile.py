#!/usr/bin/env python3
"""Conan recipe — Data::Peek Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources into a shared library
loaded by Perl's XSLoader/DynaLoader.

Adaptations for OHOS:
- Patch Makefile.PL to add dynamic_lib OTHERLDFLAGS for missing CRT files (E097)
- Pass INC flags for OHOS SDK sysroot headers
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DataPeekConan(ConanFile):
    name = "data-peek"
    version = "0.53"
    description = "Perl XS module for debugging and visualizing Perl internal data structures"
    license = "perl"
    homepage = "https://metacpan.org/pod/Data::Peek"
    url = ""  # CI fills this

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

        # OHOS SDK sysroot include paths (for standard C library headers)
        ohos_sysroot_inc = "-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include -I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/aarch64-linux-ohos"

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}" INC="{ohos_sysroot_inc}"')

        # Step 2: Build
        self.run("make -j1")

        # Step 3: Install to staging dir
        self.run("make install")

    def package(self):
        # Copy installed files from build staging to package folder
        copy(self, "*.so", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.bs", src=os.path.join(self.build_folder, "lib", "perl5"),
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
        # No cpp_info.libs — this is not a linkable C library
