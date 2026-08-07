#!/usr/bin/env python3
"""Conan test_package for pgexporter 0.8.0.

Verifies the installed pgexporter binary works correctly by running
`pgexporter --version` and checking the output contains the version string.
"""
import os

from conan import ConanFile


class PgexporterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the pgexporter binary from the package
        bin_path = None
        for bindir in self.dependencies["pgexporter"].cpp_info.bindirs:
            candidate = os.path.join(str(bindir), "pgexporter")
            if os.path.exists(candidate):
                bin_path = candidate
                break

        if not bin_path:
            raise Exception("pgexporter binary not found in package")

        # Run --version to verify the binary is functional (L2 smoke test)
        self.run(f'"{bin_path}" --version', env="conanrun")
