#!/usr/bin/env python3
"""Conan test_package for perl-server-starter — Conan L1 test.

Tests that the Server::Starter Perl module can be loaded.
"""
import os

from conan import ConanFile


class PerlServerStarterTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the start_server script exists and module loads
        self.run("perl -MServer::Starter -e 'print \"OK: Server::Starter \", $Server::Starter::VERSION, \"\\n\"'", env="conanrun")
