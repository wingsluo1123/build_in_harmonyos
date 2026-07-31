#!/usr/bin/env python3
"""Conan runtime test for teensy_loader_cli.

L1 smoke test: exercise the packaged `teensy_loader_cli` executable through
the assertions in test.sh, which verifies that `--list-mcus` prints the
supported MCU list (atmega32u4, at90usb1286, ...) and exits with status 1,
matching upstream list_mcus() behaviour.
"""
from conan import ConanFile
from conan.tools.build import can_run


class TeensyLoaderCliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv puts the package's bin/ on PATH so the packaged
        # `teensy_loader_cli` resolves; test.sh asserts --list-mcus output.
        if can_run(self):
            self.run("sh test.sh", env="conanrun")
