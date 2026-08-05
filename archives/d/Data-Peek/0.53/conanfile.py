#!/usr/bin/env python3
"""Conan recipe — Data::Peek Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources into a shared library
loaded by Perl's XSLoader/DynaLoader.

Adaptations for OHOS:
- Pass OTHERLDFLAGS via make to work around missing CRT files (crti.o, crtn.o)
- Dynamically resolve OHOS SDK sysroot path (no hardcoded version)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob
import subprocess

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

    def _find_ohos_sdk(self):
        """Dynamically find OHOS SDK native directory."""
        paths = glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native"
        )
        if not paths:
            raise ConanException(
                "OHOS SDK not found under /data/service/hnp/ohos-sdk.org/"
            )
        return os.path.realpath(paths[0])

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # OHOS-specific build: requires OHOS SDK for sysroot headers and CRT workaround
        if self.settings.os == "OHOS":
            ohos_native = self._find_ohos_sdk()
            sysroot = os.path.join(ohos_native, "sysroot")
            llvm_lib = os.path.join(
                ohos_native, "llvm", "lib", "aarch64-linux-ohos"
            )
            inc_flags = (
                f"-I{os.path.join(sysroot, 'usr', 'include')}"
                f" -I{os.path.join(sysroot, 'usr', 'include', 'aarch64-linux-ohos')}"
            )
            other_ldflags = (
                f"-nostartfiles --sysroot={sysroot}"
                f" -L{llvm_lib} -l:libunwind.a -lc"
            )
        else:
            # Linux build: standard flags, no OHOS SDK needed
            inc_flags = ""
            other_ldflags = ""

        install_base = os.path.join(self.build_folder, "lib", "perl5")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run(
            f'perl Makefile.PL INSTALL_BASE="{install_base}"'
            + (f' INC="{inc_flags}"' if inc_flags else '')
        )

        # Step 2: Build
        if other_ldflags:
            self.run(f'make -j1 OTHERLDFLAGS="{other_ldflags}"')
        else:
            self.run("make -j1")

        # Step 3: Install to staging dir
        self.run("make install")

    def package(self):
        copy(
            self,
            "*.so",
            src=os.path.join(self.build_folder, "lib", "perl5"),
            dst=os.path.join(self.package_folder, "lib", "perl5"),
        )
        copy(
            self,
            "*.pm",
            src=os.path.join(self.build_folder, "lib", "perl5"),
            dst=os.path.join(self.package_folder, "lib", "perl5"),
        )
        copy(
            self,
            "*.bs",
            src=os.path.join(self.build_folder, "lib", "perl5"),
            dst=os.path.join(self.package_folder, "lib", "perl5"),
        )

    def package_info(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")
        # Find the actual module root by locating Data/Peek.pm
        pm_files = []
        for root, dirs, files in os.walk(perl_lib):
            for f in files:
                if f == "Peek.pm":
                    pm_files.append(os.path.join(root, f))
        if pm_files:
            # Module root is the directory containing Data/Peek.pm's parent's parent
            # e.g. .../lib/perl5/aarch64-linux/Data/Peek.pm -> .../lib/perl5/aarch64-linux
            module_dir = os.path.dirname(os.path.dirname(pm_files[0]))
            self.runenv_info.append_path("PERL5LIB", module_dir)
            self.output.info(f"PERL5LIB module path: {module_dir}")
        else:
            # Fallback: use first subdirectory
            arch_dirs = glob.glob(os.path.join(perl_lib, "*"))
            for d in arch_dirs:
                if os.path.isdir(d):
                    self.runenv_info.append_path("PERL5LIB", d)
                    self.output.info(f"PERL5LIB arch path: {d}")
                    break
