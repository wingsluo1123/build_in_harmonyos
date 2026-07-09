#!/usr/bin/env python3
"""Conan test_package for fd 10.2.0 — smoke test via --version.

fd is a command-line file finder tool. This test verifies
the packaged binary runs correctly via the fd_loader wrapper.

The fd_loader is a custom ELF loader that includes the AT_PHENT
auxiliary vector fix, which is required for fd's large TLS segment.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class FdTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get the package folder from the dependency
        dep = self.dependencies["fd"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        wrapper = os.path.join(bin_dir, "fd-wrapper")

        # Run the fd binary via the wrapper
        self.run(f'"{wrapper}" --version', env="conanrun")
