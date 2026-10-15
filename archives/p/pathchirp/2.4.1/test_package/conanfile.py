#!/usr/bin/env python3
"""Consumer checks for the installed pathChirp command-line tools."""

from conan import ConanFile


class PathchirpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("python3 test.py", env="conanrun")
