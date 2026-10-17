#!/usr/bin/env python3
"""Consumer test recipe for the installed pwncat application.

The packaged artifact is an executable (``bin/pwncat``), so the consumer test
runs it: the test scripts resolve ``<package_folder>/bin/pwncat``, execute it as
a subprocess and assert observable behaviour (R34 — the packaged executable is
what is exercised, not a stub). ``sys.executable`` is used to launch the scripts
so no interpreter needs to be on the conanrun ``PATH``.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise RuntimeError("pwncat consumer test requires a runnable Python")
        package_folder = self.dependencies["pwncat"].package_folder
        here = os.path.dirname(os.path.realpath(__file__))
        for name in ("test_pwncat.py", "test_pwncat_ohos.py"):
            self.run(
                "'{}' '{}' '{}'".format(
                    sys.executable, os.path.join(here, name), package_folder),
                env="conanrun",
            )
