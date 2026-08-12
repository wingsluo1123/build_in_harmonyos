#!/usr/bin/env python3
"""Conan test_package for xapian-bindings 1.4.26 — Python import test.

Verifies the xapian Python bindings are importable and functional
(creates an in-memory database, which exercises the C++ extension).
"""
import os
import sys

from conan import ConanFile


class XapianBindingsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        python_exe = sys.executable
        test_script = os.path.join(os.path.dirname(__file__), "test_xapian_bindings.py")
        self.run(f'{python_exe} "{test_script}"', env="conanrun")
