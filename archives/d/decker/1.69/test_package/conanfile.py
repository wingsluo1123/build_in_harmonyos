#!/usr/bin/env python3
"""Conan test_package for Decker — verifies lilt binary runs correctly.

Tests that the lilt standalone interpreter binary was properly installed
and can execute a basic Lil script.
"""
import os
from conan import ConanFile


class DeckerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that lilt binary exists and can run a Lil script
        lilt_path = os.path.join(self.cpp.build.bindirs[0], "lilt")
        self.run(f"{lilt_path} --version", env="conanrun")
        # Test basic Lil script execution
        self.run(f'echo \'print["Hello from Decker on OHOS!"]\' | {lilt_path}', env="conanrun")