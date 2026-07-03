#!/usr/bin/env python3
"""Conan recipe — perl-params-validate 1.31 (Perl Module::Build).

Params-Validate is a Perl XS module for validating method/function parameters.
It uses Module::Build (Build.PL) as its build system and produces both
pure-Perl and XS implementations.

Build system: Perl Module::Build (perl Build.PL && ./Build && ./Build install)

HarmonyOS adaptation (E137): Perl 5.42.0 on OHOS has -fstack-protector-strong
in lddlflags which ld.lld rejects. We patch inc/MyMBClass.pm to override
the CBuilder config, removing the flag and adding proper -L/-I paths.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, load


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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os in ("Linux", "OHOS"):
            self._patch_for_ohos()

        # Step 1: Generate Build script
        self.run("perl Build.PL")

        # Step 2: Compile XS and pure-Perl modules
        self.run("./Build")

    def package(self):
        # Install to packaging directory using --destdir
        self.run(f"./Build install --destdir={self.package_folder}")

    def package_info(self):
        # This is a Perl module, not a C library.
        pass

    def _patch_for_ohos(self):
        """Patch inc/MyMBClass.pm to override CBuilder config for HarmonyOS.

        Perl 5.42.0 on OHOS has -fstack-protector-strong in lddlflags which
        ld.lld rejects (E137). Also, musl C library headers and system
        libraries are not in default search paths. We override the
        cbuilder() method to fix these issues.
        """
        home = os.environ.get("HOME", "")
        sys_inc = os.path.join(home, "usr", "local", "include")
        sys_lib = os.path.join(home, "usr", "local", "lib")

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
