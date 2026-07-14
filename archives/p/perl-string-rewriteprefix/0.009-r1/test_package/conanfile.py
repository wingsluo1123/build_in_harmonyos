#!/usr/bin/env python3
"""Conan test_package — perl-string-rewriteprefix 0.009-r1 (pure Perl module).

Perl-based functional test: verifies String::RewritePrefix works correctly
on OHOS by running test.pl which exercises the core rewrite API.
"""
import os

from conan import ConanFile


class PerlStringRewriteprefixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No compilation needed for a pure Perl module test
        pass

    def test(self):
        # Run the Perl-based functional test
        test_script = os.path.join(self.source_folder, "test.pl")

        # Build PERL5LIB: system deps + conan package path
        perl5lib = (
            "/storage/Users/currentUser/usr/local/perl5/lib/perl5:"
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux:"
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"
        )

        # Add the conan package's Perl lib path (Conan 2 API)
        try:
            dep = self.dependencies["perl-string-rewriteprefix"]
            pkg_folder = str(dep.package_folder)
            pkg_perl_lib = os.path.join(
                pkg_folder,
                "data", "service", "hnp", "perl.org",
                "perl_5.42.0", "lib", "site_perl", "5.42.0"
            )
            if os.path.isdir(pkg_perl_lib):
                perl5lib = pkg_perl_lib + ":" + perl5lib
        except (KeyError, AttributeError):
            pass  # Package not yet resolved — fall back to system Perl paths

        # Use shell inline env vars (Conan 2 env=list doesn't always work)
        cmd = (
            'PERL_PARAMS_UTIL_PP=1 '
            'PERL5LIB="{}" '
            'perl {}'
        ).format(perl5lib, test_script)

        self.run(cmd)
