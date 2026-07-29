#!/usr/bin/env python3
"""Conan consumer test for GNU nano 9.0."""

from conan import ConanFile
from conan.tools.build import can_run


class NanoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("nano --version", env="conanrun")
