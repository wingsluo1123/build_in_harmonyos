#!/usr/bin/env python3
"""Conan consumer test for piexif — import the installed module and exercise
the public API on the OHOS-built package (dump/load round-trip, insert into a
JPEG, remove, negative controls)."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PiexifTestConan(ConanFile):
    # The tested package is a python-require; declare the recommended wiring
    # so conan 2.29 does not emit the deprecation warning.
    python_requires = "tested_reference_str"

    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-built consumer cannot run on the build host.")
            return
        dep = self.dependencies["piexif"]
        package_folder = dep.package_folder
        site_packages = None
        for root, _, _ in os.walk(package_folder):
            if (os.path.basename(root) == "site-packages"
                    and os.path.isdir(os.path.join(root, "piexif"))):
                site_packages = root
                break
        if not site_packages:
            raise ConanException(
                "piexif site-packages not found under %s" % package_folder)
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_piexif.py")
        # -B: do not write __pycache__ into the installed package folder.
        self.run('%s -B "%s" "%s"' % (sys.executable, script, site_packages),
                 env="conanrun")
