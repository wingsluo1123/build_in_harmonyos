#!/usr/bin/env python3
"""Conan test_package for docuum 0.27.0 — binary smoke test (R34)."""

import os

from conan import ConanFile


class DocuumTestPkgConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh cannot execute ELF binaries, use bash wrapper
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        docuum = os.path.join(self.dependencies["docuum"].package_folder, "bin", "docuum")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_script}" "{docuum}"', env="conanrun")
