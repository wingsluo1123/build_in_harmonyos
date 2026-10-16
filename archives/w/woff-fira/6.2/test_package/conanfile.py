#!/usr/bin/env python3
"""Conan consumer test for the Fira Code 6.2 WOFF package."""

import os
import sys

from conan import ConanFile


class WoffFiraTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["woff-fira"]
        font_dirs = package.cpp_info.resdirs or []
        if not font_dirs:
            raise Exception("woff-fira did not expose its WOFF resource directory")

        for font_dir in font_dirs:
            if not os.path.isabs(font_dir):
                font_dir = os.path.join(package.package_folder, font_dir)
            if not os.path.isdir(font_dir):
                raise Exception(f"woff-fira resource directory is missing: {font_dir}")

        test_script = os.path.join(self.source_folder, "test_fonts.py")
        self.run(f'"{sys.executable}" "{test_script}" "{package.package_folder}"')
