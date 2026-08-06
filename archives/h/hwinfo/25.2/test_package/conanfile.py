#!/usr/bin/env python3
"""test_package for hwinfo — runs hwinfo to verify the binary."""
import os

from conan import ConanFile


class HwinfoTestConan(ConanFile):
    """test_package for hwinfo — runs hwinfo --version to verify the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Get the hwinfo binary path directly from the package folder
        hwinfo = os.path.join(str(self.dependencies["hwinfo"].package_folder), "bin", "hwinfo")
        self.run(f'{bash} -c "{hwinfo} --version"', env="conanrun")
