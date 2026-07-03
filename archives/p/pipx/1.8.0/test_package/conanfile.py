#!/usr/bin/env python3
"""Conan test_package for pipx — runs `pipx --version` to verify installation."""
import os

from conan import ConanFile


class PipxTestConan(ConanFile):
    """Test package for pipx — verifies pipx --version works."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder for the pipx dependency
        pipx_pkg = self.dependencies["pipx"].package_folder
        site_packages = os.path.join(pipx_pkg, "lib", "python3.12", "site-packages")
        # Run pipx --version directly with PYTHONPATH set
        self.run(f'PYTHONPATH="{site_packages}" python3 -m pipx --version', env="conanrun")
