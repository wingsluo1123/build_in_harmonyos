#!/usr/bin/env python3
"""Conan test_package — perl-orlite (ORLite) 2.00-r0

L1 test: verify ORLite.pm is packaged and its API is correct.
Uses mock DBD::SQLite to test ORLite's pure Perl logic without
requiring the DBD::SQLite .so (E046 SELinux platform limitation).
"""
import os

from conan import ConanFile


class PerlorliteTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # Pure Perl module — no compilation needed

    def test(self):
        # L1+L2 smoke test: run test_orlite.sh which verifies
        # ORLite.pm presence and API via mock DBD::SQLite
        self.run("sh test_orlite.sh", env="conanrun")
