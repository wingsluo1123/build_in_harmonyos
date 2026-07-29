#!/usr/bin/env python3
from conan import ConanFile

class TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def test(self):
        self.run("echo OK", env="conanrun")
