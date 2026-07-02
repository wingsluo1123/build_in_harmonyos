#!/usr/bin/env python3
"""Conan test_package for perl-net-xmpp (pure Perl module).

L1 test: Verify the Perl module can be loaded and reports correct version.
"""
import os

from conan import ConanFile


class PerlNetXmppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for Perl module test

    def test(self):
        # Get the package folder from the dependency
        pkg = self.dependencies["perl-net-xmpp"]
        pkg_folder = pkg.package_folder

        # Search for the Net/XMPP.pm file to find the correct lib path
        perl_lib = None
        for root, dirs, files in os.walk(pkg_folder):
            if "XMPP.pm" in files and root.endswith(os.path.join("Net")):
                perl_lib = os.path.dirname(root)
                break

        if perl_lib:
            cmd = (f'perl -I"{perl_lib}" -MNet::XMPP -e '
                   f'\'print "Net::XMPP version: ", Net::XMPP->VERSION, "\\n"; '
                   f'die "version mismatch" unless Net::XMPP->VERSION eq "1.05";\'')
        else:
            cmd = ('perl -MNet::XMPP -e '
                   '\'print "Net::XMPP version: ", Net::XMPP->VERSION, "\\n";\'')

        self.run(cmd, env="conanrun")
