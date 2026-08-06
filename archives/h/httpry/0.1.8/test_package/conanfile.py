#!/usr/bin/env python3
"""Conan test_package for httpry 0.1.8.

Verifies that the httpry binary is installed and functional by running
it with -h flag (exit code 0 indicates the binary works and displays version info).
"""
from conan import ConanFile
from conan.tools.build import can_run


class HttpryTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("httpry -h", env="conanrun")
