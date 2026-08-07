#!/usr/bin/env python3
"""Conan recipe — meta Perl XS module (perl-meta).

Build system: ExtUtils::MakeMaker (Makefile.PL) + manual XS compilation
This is a Perl XS module that compiles C sources (meta.xs) into a shared
library (meta.so) loaded by Perl's XSLoader/DynaLoader.

Adaptations for OHOS:
- Module::Build not available in Perl 5.42.2 core (removed in 5.28);
  replaced with ExtUtils::MakeMaker (Makefile.PL created inline)
- XS compilation done manually (xsubpp + clang) because MakeMaker's XS
  auto-compilation doesn't work correctly with conan perl (prefix=/
  breaks Config archlibexp, PERL_INC, and dependency rules)
- CC/LD passed inline to override perl's Config compiler path
- LDDLFLAGS overridden to remove -fstack-protector-strong (ld.lld rejects it)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import glob
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlMetaConan(ConanFile):
    name = "perl-meta"
    version = "0.015-r0"
    description = "Perl XS module providing a meta-programming API for Perl"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/meta"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "perl-meta recipe currently supports Linux and OHOS native builds only"
            )

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _find_perl_paths(self):
        """Find perl CORE and archlib dirs from conan perl dependency."""
        perl_pkg = self.dependencies["perl"].package_folder
        core_dirs = glob.glob(
            os.path.join(perl_pkg, "lib", "perl5", "*", "*", "CORE")
        )
        for d in core_dirs:
            if os.path.isfile(os.path.join(d, "EXTERN.h")):
                archlib = os.path.dirname(d)
                perl_bin = os.path.join(perl_pkg, "bin", "perl")
                return d, archlib, perl_bin, perl_pkg
        return None, None, None, None

    def build(self):
        apply_conandata_patches(self)

        # Get compiler from conan toolchain configuration
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or os.environ.get("CC") or "clang"

        # Find perl paths (conan perl prefix=/ breaks Config archlibexp)
        perl_core, perl_archlib, perl_bin, perl_pkg = self._find_perl_paths()

        # Create Makefile.PL (replacing Build.PL which requires Module::Build,
        # not available in Perl 5.42.2 core — removed in Perl 5.28)
        makefile_pl = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME         => 'meta',
    VERSION_FROM => 'lib/meta.pm',
    LICENSE      => 'perl_5',
    PREREQ_PM    => {
        'perl' => '5.014',
    },
    TEST_REQUIRES => {
        'Test2::V0' => 0,
    },
    INSTALLDIRS  => 'site',
    XS           => { 'lib/meta.xs' => 'lib/meta.c' },
    OBJECT        => '$(BASEEXT)$(OBJ_EXT)',
    clean         => { FILES => 'lib/meta.c' },
);
"""
        makefile_path = os.path.join(self.source_folder, "Makefile.PL")
        with open(makefile_path, "w") as f:
            f.write(makefile_pl)

        install_base = os.path.join(self.build_folder, "lib", "perl5")

        # Step 1: Generate Makefile (PERL_SRC env for _perl_header_files)
        env_prefix = f'CC="{cc}" LD="{cc}"'
        if perl_core:
            env_prefix += f' PERL_SRC="{perl_core}"'
        self.run(
            f'{env_prefix} perl Makefile.PL INSTALL_BASE="{install_base}"',
            env="conanrun",
        )

        # Step 2: Copy .pm/.xs to blib/ (pm_to_blib target only)
        self.run(
            f'make pm_to_blib CC="{cc}" LD="{cc}"',
            env="conanrun",
        )

        # Step 3: Manually compile XS code (MakeMaker XS compilation doesn't
        # work with conan perl due to Config path issues)
        if perl_core and perl_bin:
            # Find xsubpp and typemap
            xsubpp = os.path.join(perl_archlib, "xsubpp")
            typemap = os.path.join(perl_archlib, "typemap")
            if not os.path.isfile(xsubpp):
                # Try ExtUtils directory
                extutils_dir = os.path.join(perl_pkg, "lib", "perl5", "5.42.2", "ExtUtils")
                xsubpp = os.path.join(extutils_dir, "xsubpp")
                typemap = os.path.join(extutils_dir, "typemap")

            src_dir = self.source_folder
            xs_file = os.path.join(src_dir, "lib", "meta.xs")
            c_file = os.path.join(src_dir, "lib", "meta.c")
            o_file = os.path.join(src_dir, "meta.o")
            so_dir = os.path.join(src_dir, "blib", "arch", "auto", "meta")
            so_file = os.path.join(so_dir, "meta.so")
            os.makedirs(so_dir, exist_ok=True)

            # Get perl ccflags for compilation
            ccflags_result = subprocess.run(
                [perl_bin, "-MConfig", "-e",
                 'print $Config{ccflags}'],
                capture_output=True, text=True, env={"PERL5LIB": os.environ.get("PERL5LIB", "")}
            )
            ccflags = ccflags_result.stdout.strip()
            # musl doesn't have off64_t (glibc LFS type); define it as off_t
            ccflags += " -Doff64_t=off_t"

            # 3a: Generate C from XS (xsubpp)
            xsubpp_cmd = f'"{perl_bin}" "{xsubpp}" -typemap "{typemap}" "{xs_file}" > "{c_file}"'
            self.run(xsubpp_cmd, env="conanrun")

            # 3b: Compile C to object
            compile_cmd = f'"{cc}" -c -I"{perl_core}" {ccflags} "{c_file}" -o "{o_file}"'
            self.run(compile_cmd, env="conanrun")

            # 3c: Link object to shared library
            link_cmd = f'"{cc}" -shared -O2 "{o_file}" -o "{so_file}"'
            self.run(link_cmd, env="conanrun")

        # Step 4: Install to staging dir
        make_overrides = f'CC="{cc}" LD="{cc}"'
        if perl_core:
            make_overrides += f' PERL_INC="{perl_core}" PERL_INCDEP="{perl_core}"'
        if perl_archlib:
            make_overrides += f' PERL_ARCHLIB="{perl_archlib}" PERL_ARCHLIBDEP="{perl_archlib}" PERL_LIB="{perl_archlib}"'
        self.run(f'make install {make_overrides}', env="conanrun")

    def package(self):
        # Copy installed files from build staging to package folder
        copy(self, "*.so", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.pm", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        copy(self, "*.xs", src=os.path.join(self.build_folder, "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # This is a Perl XS module, not a C library.
        # The .so is loaded by Perl's XSLoader at runtime.
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.output.info(f"Perl library path: {perl_lib}")

        # ExtUtils::MakeMaker installs modules under lib/perl5/$arch/
        arch_dirs = glob.glob(os.path.join(perl_lib, "*"))
        for d in arch_dirs:
            if os.path.isdir(d):
                self.runenv_info.append_path("PERL5LIB", d)
                self.output.info(f"PERL5LIB arch path: {d}")
                break

        # No cpp_info.libs — this is not a linkable C library
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
