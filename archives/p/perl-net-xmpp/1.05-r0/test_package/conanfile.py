#!/usr/bin/env python3
"""Conan test_package for perl-net-xmpp (pure Perl module).

L1 test: Verify the package contains Net/XMPP.pm and all expected submodules
with the correct version. Uses file-based verification since runtime
dependencies (XML::Stream, Authen::SASL) are not available in the CI
environment to load the module at test time.
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
        pkg = self.dependencies["perl-net-xmpp"]
        pkg_folder = pkg.package_folder

        # Search for the Net/XMPP.pm file to find the correct lib path
        xmpp_pm = None
        for root, dirs, files in os.walk(pkg_folder):
            if "XMPP.pm" in files and root.endswith(os.path.join("Net")):
                xmpp_pm = os.path.join(root, "XMPP.pm")
                break

        if not xmpp_pm:
            raise Exception("Net/XMPP.pm not found in package")

        perl_lib = os.path.dirname(os.path.dirname(xmpp_pm))

        # Verify all expected .pm files are present in the package
        expected_modules = [
            "Net/XMPP.pm", "Net/XMPP/Connection.pm", "Net/XMPP/Debug.pm",
            "Net/XMPP/IQ.pm", "Net/XMPP/JID.pm", "Net/XMPP/Message.pm",
            "Net/XMPP/Namespaces.pm", "Net/XMPP/Presence.pm",
            "Net/XMPP/PrivacyLists.pm", "Net/XMPP/Protocol.pm",
            "Net/XMPP/Roster.pm", "Net/XMPP/Stanza.pm", "Net/XMPP/Client.pm",
        ]
        for mod in expected_modules:
            mod_path = os.path.join(perl_lib, mod)
            if not os.path.isfile(mod_path):
                raise Exception(f"Expected module file not found: {mod}")

        # Verify version string in XMPP.pm
        self.run(f'grep -q "1.05" "{xmpp_pm}"', env="conanrun")
