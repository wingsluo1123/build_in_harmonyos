#!/usr/bin/env python3
"""Conan test_package for mailx — functional CLI tests.

mailx is a command line tool (no library API), so the L1 test runs the
installed binary through test_mailx.py which exercises usage output,
empty-mailbox handling and reading/printing a crafted mailbox.
"""
import os
import sys

from conan import ConanFile


class MailxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "mailx")
        script = os.path.join(self.recipe_folder, "test_mailx.py")

        self.run(
            f'"{sys.executable}" "{script}" "{executable}"',
            env="conanrun",
        )
