#!/usr/bin/env python3
"""Test package for txt2man 1.7.1"""
from conan import ConanFile


class Txt2ManTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: Run txt2man -h (R34: actually uses the tested package's binary)
        self.run("txt2man -h", env="conanrun")

        # Test 2: Convert text to man page format and verify output
        test_input = "NAME\n  test - txt2man conversion test\n\nDESCRIPTION\n  This is a test.\n"
        with open("test_input.txt", "w") as f:
            f.write(test_input)

        self.run("txt2man -t test -s 1 test_input.txt > output.1", env="conanrun")

        with open("output.1") as f:
            content = f.read()
        assert ".TH" in content or ".SH" in content, \
            f"Expected man page macros in output, got: {content[:200]}"
