#!/usr/bin/env python3
"""Conan test_package for nxp-mfgtools (uuu) 1.5.243.

uuu is a CLI tool. The L1 test runs `uuu -h` to verify the binary
links correctly against all dependencies (libusb, zlib, bzip2, zstd,
tinyxml2, openssl) and produces the version/help output.
"""
import os

from conan import ConanFile


class NxpmfgtoolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh cannot execute ELF binaries; use bash
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
