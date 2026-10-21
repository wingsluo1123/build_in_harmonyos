#!/usr/bin/env python3
"""Conan test_package for pingu 1.5.1.

pingu is an application (daemon + two helper binaries), not a library, so the
test executes the installed executables instead of linking against an API.
Upstream ships no automated test suite (see test_package/MANIFEST.yml), so the
cases below are the executable regression check that ships with the package.
"""
import os

from conan import ConanFile


class PinguTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test_pingu.sh")
        self.run(f'bash "{script}"', env="conanrun")
