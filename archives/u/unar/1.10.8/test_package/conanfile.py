#!/usr/bin/env python3
"""test_package for unar — runs the installed unar/lsar binaries.

Consumer verification: invoke the installed binaries the way a real user
would (--version), then run functional archive round-trips (zip and nested
tar.gz): list with lsar, extract with unar, verify contents on disk.
"""
import os

from conan import ConanFile


class UnarTestConan(ConanFile):
    """test_package for unar — runs test.sh which invokes the unar/lsar binaries."""
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
