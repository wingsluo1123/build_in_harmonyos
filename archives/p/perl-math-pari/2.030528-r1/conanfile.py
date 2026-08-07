#!/usr/bin/env python3
"""Conan recipe — Math::Pari Perl XS module.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module that compiles C sources (PARI library + XS glue)
into a shared library loaded by Perl's XSLoader/DynaLoader.

The Makefile.PL automatically downloads and embeds PARI 2.3.5 source,
patches it, and builds libPARI.a as part of the build process.

Adaptations for OHOS:
- LDDLFLAGS modified to add -nostartfiles -L<path> -lc (musl CRT files missing, E002)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""

import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlMathPariConan(ConanFile):
    name = "perl-math-pari"
    version = "2.030528-r1"
    description = "Perl interface to PARI/GP mathematical library for number theory computations"
    license = "GPL-2.0-or-later AND Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/Math::Pari"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # PARI 2.3.5 is embedded; perl is a system dependency

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
        # Makefile.PL automatically downloads and configures PARI 2.3.5
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"')

        # Step 2: Fix LDDLFLAGS for OHOS CRT files missing (E002)
        # OpenHarmony musl does not provide standard CRT startup files (crti.o, crtbeginS.o)
        # Add -nostartfiles and -L<path> -lc to link stage
        # Use expanduser to resolve OHOS user lib path dynamically (not hardcoded)
        libc_dir = os.path.join(os.path.expanduser("~"), "usr", "local", "lib")
        makefile_path = os.path.join(self.build_folder, "Makefile")
        with open(makefile_path, "r") as f:
            content = f.read()
        old_lddl = "LDDLFLAGS = -shared -O2 -fstack-protector-strong"
        new_lddl = f"LDDLFLAGS = -shared -nostartfiles -L{libc_dir} -lc -O2 -fstack-protector-strong"
        if old_lddl not in content:
            # Fallback: try regex-style match for any LDDLFLAGS with -shared
            import re
            content = re.sub(
                r"^LDDLFLAGS\s*=.*$",
                new_lddl,
                content,
                flags=re.MULTILINE,
            )
        else:
            content = content.replace(old_lddl, new_lddl)
        with open(makefile_path, "w") as f:
            f.write(content)

        # Step 3: Build
        self.run("make -j1")

        # Step 4: Install to staging dir (no DESTDIR needed — INSTALL_BASE is absolute)
        self.run("make install")

    def package(self):
        # Copy installed files from build staging to package folder
        copy(self, "*.so", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pod", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

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
