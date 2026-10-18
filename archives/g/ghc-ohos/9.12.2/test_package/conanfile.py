#!/usr/bin/env python3
"""Consumer test for ghc-ohos/9.12.2.

The assertions live in test_ghc_ohos.py so the package ships a real test
source file (CI L0c requires one; conanfile.py alone does not count).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GhcOhosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkgdir = self.dependencies["ghc-ohos"].package_folder
        script = os.path.join(self.source_folder, "test_ghc_ohos.py")
        self.run('"%s" "%s" "%s"' % (self._python(), script, pkgdir),
                 env="conanrun")

    @staticmethod
    def _python():
        import shutil
        import sys
        return shutil.which("python3") or sys.executable
