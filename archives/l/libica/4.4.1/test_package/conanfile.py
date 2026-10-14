#!/usr/bin/env python3
"""Conan test_package for libica 4.4.1 — verifies the failed-adaptation record.

Mirrors the established repository pattern (archives/b/bltool): the tested
package is a *record*, and this consumer-side test executes a real script
against the installed package contents on the target platform.
"""

import os
import sys

from conan import ConanFile


class LibicaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_failed_adaptation_record.py")
        # Quoted so spaces survive.  Paths come from Conan itself
        # (self.source_folder / package_folder), so there is no untrusted input
        # to interpolate.  Must keep the literal self.run(...) call: the repo's
        # L0d gate in ci/conan/build_and_test.sh greps for "self.run" to reject
        # stub test() methods, so replacing this with subprocess would fail CI.
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"')
        self.output.info("libica 4.4.1 failed-adaptation record verified on target")
