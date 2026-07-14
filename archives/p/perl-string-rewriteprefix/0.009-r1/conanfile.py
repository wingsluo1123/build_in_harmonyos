#!/usr/bin/env python3
"""Conan recipe — perl-string-rewriteprefix 0.009-r1 (pure Perl module).

String::RewritePrefix — rewrite strings based on a set of known prefixes.
Build system: ExtUtils::MakeMaker (perl Makefile.PL && make && make install).

Dependencies:
  - Sub::Exporter >= 0.972 (runtime, pure Perl)
  - Params::Util (transitive via Sub::Exporter, needs PERL_PARAMS_UTIL_PP=1
    on OHOS due to SELinux restricting XS .so loading on HMDFS)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlStringRewriteprefixConan(ConanFile):
    name = "perl-string-rewriteprefix"
    version = "0.009-r1"
    description = "String::RewritePrefix - rewrite strings based on a set of known prefixes"
    license = "Perl_5"
    homepage = "https://metacpan.org/dist/String-RewritePrefix"
    url = ""  # CI fills this

    # R32: settings.os check must use "in" not "=="
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Sub::Exporter is a runtime dependency (pure Perl module)
        # On OHOS, it's available in the system Perl local lib
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make
        # On OHOS: PERL_PARAMS_UTIL_PP=1 bypasses Params::Util XS .so
        #   loading restriction (SELinux on HMDFS, same issue as perl-dbd-pg)
        # PERL5LIB includes Sub::Exporter and its dependency chain
        perl_env = [
            "PERL_PARAMS_UTIL_PP=1",
            "PERL5LIB=/storage/Users/currentUser/usr/local/perl5/lib/perl5:"
                      "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux:"
                      "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0",
        ]
        self.run("perl Makefile.PL", cwd=self.source_folder, env=perl_env)
        self.run("make -j1", cwd=self.source_folder, env=perl_env)

    def package(self):
        # Install to DESTDIR for staging
        perl_env = [
            "PERL_PARAMS_UTIL_PP=1",
            "PERL5LIB=/storage/Users/currentUser/usr/local/perl5/lib/perl5:"
                      "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux:"
                      "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0",
        ]
        self.run("make install DESTDIR={}".format(self.package_folder), cwd=self.source_folder, env=perl_env)

    def package_info(self):
        # Pure Perl module — no C libraries to export
        self.cpp_info.libs = []
        # Set environment for consumers
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
