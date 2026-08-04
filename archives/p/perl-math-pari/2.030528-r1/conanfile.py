#!/usr/bin/env python3
"""Conan recipe — Math::Pari 2.030528-r1 (Perl XS module)

Build system: perl Makefile.PL (ExtUtils::MakeMaker)
PARI library is embedded in the source tarball (no external dependency).

Note: On OpenHarmony, CRT startup files may be missing. The build method
patches LDDLFLAGS to add -nostartfiles if the default link fails.
"""
import os
import glob
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PerlMathPariConan(ConanFile):
    name = "perl-math-pari"
    version = "2.030528-r1"
    description = "Perl interface to PARI/GP mathematical library"
    license = "GPL-2.0-or-later AND Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/Math::Pari"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"perl-math-pari does not support os={self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("CFLAGS", "-fPIC -O2")
        envvars = env.vars(self)
        envvars.save_script("perl_math_pari_env")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        self.run("perl Makefile.PL", cwd=src, env=["perl_math_pari_env"])

        # Patch LDDLFLAGS in Makefile for OHOS CRT compatibility
        makefile = os.path.join(src, "Makefile")
        if os.path.isfile(makefile):
            with open(makefile, "r") as f:
                content = f.read()
            # Add -nostartfiles to LDDLFLAGS to skip missing CRT files
            content = re.sub(
                r"(LDDLFLAGS\s*=\s*.*)",
                r"\1 -nostartfiles",
                content,
                count=1,
            )
            with open(makefile, "w") as f:
                f.write(content)

        self.run("make", cwd=src, env=["perl_math_pari_env"])

    def package(self):
        src = self.source_folder
        # Install to temp dir, not package_folder, to avoid extra lib/ dirs
        dest = os.path.join(self.build_folder, "destdir")
        self.run(
            f"make install DESTDIR={dest}",
            cwd=src,
            env=["perl_math_pari_env"],
        )
        blib = os.path.join(src, "blib")
        # Copy .pm files to lib/
        pm_src = os.path.join(blib, "lib")
        if os.path.isdir(pm_src):
            copy(self, "*.pm", pm_src, os.path.join(self.package_folder, "lib"))
        # Copy .so files to lib/auto/
        so_files = glob.glob(os.path.join(blib, "arch", "auto", "**", "*.so"), recursive=True)
        if so_files:
            for so in so_files:
                rel = os.path.relpath(so, os.path.join(blib, "arch"))
                target = os.path.join(self.package_folder, "lib", rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                copy(self, os.path.basename(so), os.path.dirname(so), os.path.dirname(target))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append("PERL5LIB", perl_lib)
        self.buildenv_info.append("PERL5LIB", perl_lib)
