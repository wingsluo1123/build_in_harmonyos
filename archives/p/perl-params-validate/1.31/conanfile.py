#!/usr/bin/env python3
"""Conan recipe for perl-params-validate — Perl XS module (Module::Build).

Build system: perl Build.PL + perl Build + perl Build install
XS module: Validate.xs → XS.c → XS.so
Has pure Perl fallback via Module::Implementation (auto-fallback when XS unavailable).

On OHOS:
  - musl C library headers at ~/usr/local/include (sys/types.h etc.)
  - musl libc at ~/usr/local/lib
  - E137: Perl 5.42.0 lddlflags has -fstack-protector-strong, ld.lld rejects it
  - Fix: override inc/MyMBClass.pm cbuilder() to remove flag + add -L/-I paths
  - XS .so may fail to load at runtime due to SELinux/HMDFS (PP fallback works)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout


class PerlParamsValidateConan(ConanFile):
    name = "perl-params-validate"
    version = "1.31"
    description = "Validate method/function parameters (Perl XS module)"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/release/Params-Validate"
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

        # Patch inc/MyMBClass.pm for OHOS platform (E137 fix)
        if self.settings.os in ("Linux", "OHOS"):
            self._patch_for_ohos()

        # Step 1: Generate Build script
        self.run("perl Build.PL", cwd=self.source_folder)

        # Step 2: Compile XS and pure-Perl modules
        self.run("perl Build", cwd=self.source_folder)

    def package(self):
        # Install with --destdir to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f"perl Build install --destdir={dest}", cwd=self.source_folder)

        # Also copy .so to standard lib/ for package integrity checks (L5)
        site_arch_src = os.path.join(
            dest, "data", "service", "hnp", "perl.org",
            "perl_5.42.0", "lib", "site_perl", "5.42.0", "aarch64-linux"
        )
        so_src = os.path.join(site_arch_src, "auto", "Params", "Validate", "XS", "XS.so")
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        if os.path.isfile(so_src):
            shutil.copy2(so_src, os.path.join(lib_dst, "XS.so"))

    def package_info(self):
        # Perl XS module — provides XS.so (shared library) + Perl .pm files
        # Pure Perl fallback available via Module::Implementation auto-fallback
        self.cpp_info.libs = ["XS"]
        self.cpp_info.libdirs = ["lib"]

    def _find_musl_paths(self):
        """Detect musl C library header and library paths.

        R33: Do not rely on undefined shell env vars. Instead, probe
        known OHOS locations and verify the path exists before use.
        """
        candidates_inc = [
            os.path.join(os.path.expanduser("~"), "usr", "local", "include"),
            "/data/service/hnp/usr/local/include",
            "/usr/local/include",
        ]
        candidates_lib = [
            os.path.join(os.path.expanduser("~"), "usr", "local", "lib"),
            "/data/service/hnp/usr/local/lib",
            "/usr/local/lib",
        ]

        sys_inc = next((p for p in candidates_inc if os.path.isdir(p)), "")
        sys_lib = next((p for p in candidates_lib if os.path.isdir(p)), "")
        return sys_inc, sys_lib

    def _patch_for_ohos(self):
        """Patch inc/MyMBClass.pm to override CBuilder config for HarmonyOS.

        Perl 5.42.0 on OHOS has -fstack-protector-strong in lddlflags which
        ld.lld rejects (E137). Also, musl C library headers and system
        libraries are not in default search paths. We override the
        cbuilder() method to fix these issues.
        """
        sys_inc, sys_lib = self._find_musl_paths()

        # Build the patched MyMBClass.pm content
        patched = '''package MyMBClass;

use strict;
use warnings;

use base 'Module::Build';
use ExtUtils::CBuilder;
use Config;

sub new {
    my $class = shift;
    my $self = $class->SUPER::new(@_);

    if ( defined( my $pp = $self->args('pp') ) ) {
        $self->pureperl_only($pp);
    }

    return $self;
}

# HarmonyOS (E137): Override cbuilder() to fix linker config.
# Perl 5.42.0 on OHOS has -fstack-protector-strong in lddlflags which
# ld.lld rejects. We remove it and add proper -L/-I paths.
sub cbuilder {
    my $self = shift;
    return $self->{cbuilder} if defined $self->{cbuilder};

    # Create a copy of Config hash with fixed flags
    my %config_copy;
    while (my ($k, $v) = each %Config) {
        $config_copy{$k} = $v;
    }

    # Remove -fstack-protector-strong from ldflags and lddlflags
    $config_copy{ldflags} =~ s/\\s*-fstack-protector-strong\\s*/ /g;
    $config_copy{lddlflags} =~ s/\\s*-fstack-protector-strong\\s*/ /g;

    # Add library search paths for musl libc and libunwind
    $config_copy{lddlflags} .= " -L''' + sys_lib + ''' -L/system/lib64";

    # Add include path for musl C library headers
    $config_copy{ccflags} .= " -I''' + sys_inc + '''";

    # Force clang as the linker driver (not ld.lld from env)
    $config_copy{ld} = "clang";

    my $cb = ExtUtils::CBuilder->new(config => \\%config_copy);
    $self->{cbuilder} = $cb;
    return $cb;
}

1;
'''
        mymb_path = os.path.join(self.source_folder, "inc", "MyMBClass.pm")
        save(self, mymb_path, patched)
