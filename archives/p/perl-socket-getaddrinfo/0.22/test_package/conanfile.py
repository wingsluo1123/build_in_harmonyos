#!/usr/bin/env python3
"""Conan test_package — Socket::GetAddrInfo Perl XS module.

L1 test: verify the installed Perl module can be loaded and getaddrinfo works.
"""
import os

from conan import ConanFile


class PerlSocketGetaddrinfoTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Set up PERL5LIB to find the module in the Conan package
        pkg = self.dependencies["perl-socket-getaddrinfo"].package_folder
        perl_lib = os.path.join(pkg, "lib", "site_perl", "5.42.0")
        perl_arch = os.path.join(perl_lib, "aarch64-linux")

        test_script = (
            "use strict;\n"
            "use warnings;\n"
            "use Socket qw( SOCK_STREAM );\n"
            "use Socket::GetAddrInfo qw( getaddrinfo );\n"
            "my $version = $Socket::GetAddrInfo::VERSION;\n"
            "print \"Socket::GetAddrInfo version: $version\\n\";\n"
            "my ($err, @res) = getaddrinfo(\"127.0.0.1\", \"80\", { socktype => SOCK_STREAM });\n"
            "die \"getaddrinfo failed (err=$err)\" unless $err == 0 && @res > 0;\n"
            "print \"getaddrinfo available: yes\\n\";\n"
            "print \"results: \" . scalar(@res) . \", family: $res[0]->{family}\\n\";\n"
            "print \"All smoke tests passed.\\n\";\n"
        )
        test_file = os.path.join(self.source_folder, "test_getaddrinfo.pl")
        with open(test_file, "w") as f:
            f.write(test_script)

        # Set PERL5LIB so Perl can find the module in the Conan package
        os.environ["PERL5LIB"] = f"{perl_lib}:{perl_arch}"
        self.run(f"perl {test_file}", env="conanrun")
