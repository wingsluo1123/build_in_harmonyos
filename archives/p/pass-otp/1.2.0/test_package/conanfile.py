#!/usr/bin/env python3
"""Conan test_package for pass-otp 1.2.0 — Shell script test.

Verifies that the otp.bash extension script is installed and valid.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PassotpTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["pass-otp"]
            ext_path = os.path.join(
                dep.package_folder, "usr", "lib", "password-store", "extensions", "otp.bash"
            )
            if not os.path.isfile(ext_path):
                raise Exception(f"Extension script not found: {ext_path}")
            # Verify it's a valid bash script (syntax check)
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} -n "{ext_path}"', env="conanrun")
            # Verify man page exists
            man_path = os.path.join(
                dep.package_folder, "usr", "share", "man", "man1", "pass-otp.1"
            )
            if not os.path.isfile(man_path):
                raise Exception(f"Man page not found: {man_path}")
            self.output.info("pass-otp test: PASS (otp.bash exists, valid syntax, man page present)")
