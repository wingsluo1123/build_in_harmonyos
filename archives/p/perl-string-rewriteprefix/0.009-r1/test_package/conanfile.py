#!/usr/bin/env python3
"""Conan test_package — perl-string-rewriteprefix 0.009-r1 (pure Perl module).

Perl-based functional test: verifies String::RewritePrefix works correctly
on OHOS by running test.pl which exercises the core rewrite API.
"""
import os
import tempfile

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

        # Ensure Sub::Exporter dependency chain is available.
        # CI workers may not have these pure-Perl modules pre-installed.
        dep_dir = self._ensure_perl_deps(perl5lib)
        if dep_dir:
            perl5lib = dep_dir + ":" + perl5lib

        # Use shell inline env vars (Conan 2 env=list doesn't always work)
        cmd = (
            'PERL_PARAMS_UTIL_PP=1 '
            'PERL5LIB="{}" '
            'perl {}'
        ).format(perl5lib, test_script)

        self.run(cmd)

    def _ensure_perl_deps(self, perl5lib):
        """Download and install Sub::Exporter pure-Perl dependency chain if not available."""
        # Check if Sub::Exporter is already available
        check_cmd = 'PERL_PARAMS_UTIL_PP=1 PERL5LIB="{}" perl -e "use Sub::Exporter;" 2>/dev/null'.format(perl5lib)
        try:
            self.run(check_cmd)
            return None  # Already available
        except Exception:
            pass  # Need to install

        dep_dir = tempfile.mkdtemp(prefix="perl_deps_")

        # Download and install all 4 pure-Perl modules in one shell command.
        # Dependency chain: Sub::Exporter → Data::OptList, Params::Util
        #                   Data::OptList → Sub::Install
        install_cmd = (
            'set -e; '
            'mkdir -p "{dir}/_extract"; '
            'cd "{dir}/_extract"; '
            'for mod_url in '
            '"https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Sub-Install-0.928.tar.gz" '
            '"https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Data-OptList-0.110.tar.gz" '
            '"https://cpan.metacpan.org/authors/id/R/RE/REHSACK/Params-Util-1.102.tar.gz" '
            '"https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Sub-Exporter-0.988.tar.gz"; do '
            'curl -sL "$mod_url" -o tmp.tar.gz; '
            'tar xzf tmp.tar.gz; '
            'rm -f tmp.tar.gz; '
            'done; '
            'cp -r */lib/* "{dir}/"; '
            'cd "{dir}"; '
            'rm -rf _extract'
        ).format(dir=dep_dir)

        self.run(install_cmd)
        return dep_dir
