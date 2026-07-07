#!/usr/bin/env python3
"""Conan recipe for perl-params-util — Perl XS module (Makefile.PL + XS).

Build system: perl Makefile.PL + make + make install
XS module: Util.xs → Util.c → Util.so
Has pure Perl fallback (Params::Util::PP) activated via PERL_PARAMS_UTIL_PP=1.

On OHOS:
  - musl C library headers at ~/usr/local/include (sys/types.h etc.)
  - musl libc at ~/usr/local/lib
  - CRT workaround: -nostartfiles -nodefaultlibs -lc
  - XS .so may fail to load at runtime due to ELF signing (pure Perl fallback works)
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlparamsutilConan(ConanFile):
    name = "perl-params-util"
    version = "1.102"
    description = "Simple, compact and correct param-checking functions (Perl XS module)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Params-Util"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply conandata patches (if any)
        apply_conandata_patches(self)

        # Step 1: Generate Makefile via Makefile.PL
        # XS detection may fail due to ld.lld not supporting -fstack-protector-strong,
        # but ExtUtils::MakeMaker still generates xsubpp rules for .xs files.
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Patch Makefile for OpenHarmony platform
        #   a) Add musl C library include path for system headers (sys/types.h etc.)
        #   b) Add CRT workaround: -nostartfiles -nodefaultlibs -lc
        #   c) Add musl lib path for finding libc
        makefile_path = os.path.join(self.source_folder, "Makefile")
        with open(makefile_path, "r") as f:
            content = f.read()

        musl_inc = "/storage/Users/currentUser/usr/local/include"
        musl_lib = "/storage/Users/currentUser/usr/local/lib"

        # Add musl include path to CCFLAGS
        content = re.sub(
            r"^(CCFLAGS = )(?!.*" + re.escape(musl_inc) + ")",
            rf"\1-I{musl_inc} ",
            content,
            flags=re.MULTILINE,
        )
        # Add CRT workaround and musl lib path to LDDLFLAGS
        content = re.sub(
            r"^LDDLFLAGS = -shared(.*)$",
            rf"LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -L{musl_lib} -lc\1",
            content,
            flags=re.MULTILINE,
        )

        with open(makefile_path, "w") as f:
            f.write(content)

        # Step 3: Build (R9: use -j1)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f"make install DESTDIR={dest}", cwd=self.source_folder)

        # Also copy .so to standard lib/ for package integrity checks
        import shutil
        site_arch_src = os.path.join(
            dest, "data", "service", "hnp", "perl.org",
            "perl_5.42.0", "lib", "site_perl", "5.42.0", "aarch64-linux"
        )
        so_src = os.path.join(site_arch_src, "auto", "Params", "Util", "Util.so")
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        if os.path.isfile(so_src):
            shutil.copy2(so_src, os.path.join(lib_dst, "Util.so"))

    def package_info(self):
        # Perl XS module — provides Util.so (shared library) + Perl .pm files
        # Pure Perl fallback available via PERL_PARAMS_UTIL_PP=1
        self.cpp_info.libs = ["Util"]
        self.cpp_info.libdirs = ["lib"]
