#!/usr/bin/env python3
"""Consumer test recipe for the installed tubeup package.

Builds a PYTHONPATH from the tested package plus its declared Conan
dependencies and runs the real consumer test scripts (R34: they exercise the
packaged tubeup API, not a stub).
"""
import glob
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


def _site_packages(package_folder):
    for pattern in ("lib/python*/site-packages", "site-packages"):
        found = sorted(glob.glob(os.path.join(package_folder, pattern)))
        if found:
            return found[0]
    return package_folder


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise RuntimeError("tubeup consumer test requires a runnable Python")
        paths = []
        for dependency in self.dependencies.values():
            paths.append(_site_packages(dependency.package_folder))
        pythonpath = os.pathsep.join(paths)
        package_folder = self.dependencies["tubeup"].package_folder
        here = os.path.dirname(os.path.realpath(__file__))
        for name in ("test_tubeup.py", "test_tubeup_ohos.py"):
            self.run(
                f"'{sys.executable}' '{os.path.join(here, name)}' "
                f"'{pythonpath}' '{package_folder}'",
                env="conanrun",
            )
