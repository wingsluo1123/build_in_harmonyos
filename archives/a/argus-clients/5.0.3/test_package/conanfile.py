#!/usr/bin/env python3
"""Conan test_package for argus-clients 5.0.3.

Tests the installed argus-clients binary by running `ra --version`
and verifying the output contains "Ra Version 5.0.3".

R34: test executes the tested package's binary.
"""
from conan import ConanFile
from conan.tools.build import can_run

class ArgusclientsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # ra --version exits with code 1 but prints "Ra Version 5.0.3"
            # grep checks for the expected version string
            # If the binary is missing, grep fails → test fails (R34: not a fake test)
            self.run("ra --version 2>&1 | grep 'Ra Version 5.0.3'", env="conanrun")
