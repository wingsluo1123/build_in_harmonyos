#!/usr/bin/env python3
"""Conan test_package for cargo-binstall 1.21.1 — precompiled binary smoke test.

Verifies that all three binaries (cargo-binstall, detect-targets, detect-wasi)
are installed and functional.

File location: archives/c/cargo-binstall/1.21.1/test_package/conanfile.py
"""
import os

from conan import ConanFile


class CargoBinstallTestConan(ConanFile):
    """test_package for cargo-binstall — runs test.sh which invokes all three binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use bash to wrap binary execution
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
