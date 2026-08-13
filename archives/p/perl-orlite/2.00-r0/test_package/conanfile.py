#!/usr/bin/env python3
"""Conan test_package — perl-orlite (ORLite) 2.00-r0

L1 test: verify ORLite.pm is packaged and its API is correct.
Uses static analysis (test_orlite.sh) to verify ORLite.pm without
requiring the DBD::SQLite .so (E046 SELinux platform limitation).
"""
from conan import ConanFile


class PerlorliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # Pure Perl module — no compilation needed

    def test(self):
        # L1+L2 smoke test: run test_orlite.sh which loads ORLite
        # with mock DBD::SQLite and calls 9 core API methods (R34)
        self.run("sh test_orlite.sh", env="conanrun")
