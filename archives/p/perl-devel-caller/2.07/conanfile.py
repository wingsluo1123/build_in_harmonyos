#!/usr/bin/env python3
"""Conan recipe — perl-devel-caller 2.07 (Perl XS module)

Devel::Caller provides meatier versions of caller() for Perl programs.
It uses ExtUtils::MakeMaker (Makefile.PL) as its build system.

Key OHOS adaptations:
- System headers: add -I for OHOS SDK sysroot include directory
- Linker: bypass missing CRT files with -nostartfiles -nodefaultlibs -lc
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlDevelCallerConan(ConanFile):
    name = "perl-devel-caller"
    version = "2.07"
    description = "Devel::Caller - meatier versions of caller (Perl XS module)"
    license = "perl"
    homepage = "https://metacpan.org/pod/Devel::Caller"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _find_sys_headers(self):
        """Find OHOS SDK sysroot include directory."""
        candidates = []
        for pattern in [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot/usr/include",
        ]:
            candidates.extend(sorted(glob.glob(pattern), reverse=True))
        for path in candidates:
            if os.path.isdir(path):
                return path
        return None

    def build(self):
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")

        # --- OHOS Adaptation: Modify Makefile.PL ---
        # 1. Add system header include paths (INC) for OHOS SDK sysroot
        # 2. Add dynamic_lib OTHERLDFLAGS to bypass missing CRT files
        if self.settings.os in ("Linux", "OHOS"):
            sys_headers = self._find_sys_headers()

            with open(makefile_pl, "r") as f:
                content = f.read()

            # Build INC flags
            inc_flags = []
            if sys_headers:
                inc_flags.append(f"-I{sys_headers}")

            # Add INC field if we have system headers
            if inc_flags and "INC" not in content:
                inc_str = " ".join(inc_flags)
                content = content.replace(
                    "    ABSTRACT_FROM => 'lib/Devel/Caller.pm',\n",
                    f"    ABSTRACT_FROM => 'lib/Devel/Caller.pm',\n"
                    f"    INC           => '{inc_str}',\n",
                )
            elif inc_flags and "'INC'" in content:
                inc_str = " ".join(inc_flags)
                content = content.replace(
                    "'INC'\t=> '',",
                    f"'INC'\t=> '{inc_str}',",
                )

            # Add dynamic_lib before the closing ); of WriteMakefile
            if "dynamic_lib" not in content:
                content = content.replace(
                    "   },\n);",
                    "   },\n"
                    "    dynamic_lib => { OTHERLDFLAGS => q[-nostartfiles -nodefaultlibs -lc] },\n"
                    ");",
                )

            with open(makefile_pl, "w") as f:
                f.write(content)

        # Step 1: Generate Makefile (using system perl)
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Build
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install to package directory using Perl's make install with DESTDIR
        dest = self.package_folder
        self.run(
            f'make install DESTDIR="{dest}"',
            cwd=self.source_folder,
        )

    def package_info(self):
        # Caller.so is a Perl XS shared library
        self.cpp_info.libs = ["Caller"]
