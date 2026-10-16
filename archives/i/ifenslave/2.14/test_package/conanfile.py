#!/usr/bin/env python3
"""Functional test package for ifenslave 2.14."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


def _resolve_shell():
    # HMBS preflight injects SHELL=/bin/sh and guarantees /bin/sh;
    # bash is absent on the HarmonyOS image, so never hard-depend on it.
    # The test script is POSIX sh, any Bourne shell works.
    for cand in (os.environ.get("SHELL"), "/bin/sh", "sh"):
        if not cand:
            continue
        if os.path.isfile(cand) or shutil.which(cand):
            return cand
    return "sh"


class TestPackageConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg_folder = self.dependencies["ifenslave"].package_folder
            bin_dir = os.path.join(pkg_folder, "bin")
            script = os.path.join(self.recipe_folder, "test_ifenslave.sh")
            shell = _resolve_shell()
            self.run('"%s" "%s" "%s"' % (shell, script, bin_dir), env="conanrun")
