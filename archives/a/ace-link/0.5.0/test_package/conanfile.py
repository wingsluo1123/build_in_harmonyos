#!/usr/bin/env python3
"""test_package for ace-link — verifies that ace-link.el was properly installed."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import save


class AceLinkTestConan(ConanFile):
    """test_package for ace-link — verifies ace-link.el exists."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # In Conan 2.x, check file existence via dependencies
        if can_run(self):
            # For cross-build / non-native builds, we check the
            # package folder via self.dependencies
            pass

        # Verify ace-link.el exists in the package
        dep = self.dependencies["ace-link"]
        package_folder = dep.package_folder
        site_lisp = os.path.join(package_folder, "lib", "site-lisp")
        el_file = os.path.join(site_lisp, "ace-link.el")

        if os.path.exists(el_file):
            print(f"[PASS] ace-link.el found at: {el_file}")
        else:
            # Try package root
            alt = os.path.join(package_folder, "ace-link.el")
            if os.path.exists(alt):
                print(f"[PASS] ace-link.el found at: {alt}")
            else:
                raise Exception(
                    f"ace-link.el not found in package folder {package_folder}. "
                    f"Checked: {el_file}, {alt}"
                )
