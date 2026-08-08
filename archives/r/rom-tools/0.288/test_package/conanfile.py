#!/usr/bin/env python3
"""Test package for rom-tools 0.288 — verifies chdman and romcmp CLI tools work."""
import os

from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.files import save


class RomToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Generate a simple Makefile to compile the test
        bindir = self.dependencies["rom-tools"].cpp_info.bindirs[0]
        save(self, "Makefile", f"""
CFLAGS = -O2 -Wall
test: test.c
\t$(CC) $(CFLAGS) -o test test.c

run: test
\tPATH="{bindir}:$$PATH" ./test
""")

    def build(self):
        self.run("make test")

    def test(self):
        self.run("make run")
