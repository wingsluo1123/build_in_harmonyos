#!/usr/bin/env python3
"""Conan test_package for midicsv — executable smoke test.

Tests that midicsv and csvmidi are installed and functional by
running a MIDI→CSV→MIDI round-trip conversion.
"""
import os

from conan import ConanFile


class MidicsvTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
