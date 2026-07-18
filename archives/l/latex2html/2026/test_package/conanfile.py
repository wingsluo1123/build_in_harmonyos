#!/usr/bin/env python3
"""Conan test_package for latex2html 2026 — L1 official test."""
import os
from conan import ConanFile


class Latex2HtmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["latex2html"]
        pkg_dir = pkg.package_folder
        # Find latex2html binary and share dir
        latex2html_bin = None
        share_dir = None
        for root, dirs, files in os.walk(pkg_dir):
            if "latex2html" in files and root.endswith("/bin"):
                latex2html_bin = os.path.join(root, "latex2html")
                # Share dir is parallel to bin: ../share/lib/latex2html
                share_dir = os.path.normpath(os.path.join(root, "..", "share", "lib", "latex2html"))
            # Also try to find share dir directly
            if "l2hconf.pm" in files:
                share_dir = root
        if latex2html_bin:
            # l2hconf.pm is at lib/latex2html/, but binary hardcodes share/lib/latex2html/
            lib_dir = os.path.normpath(os.path.join(root, "..", "lib", "latex2html"))
            if os.path.isdir(lib_dir):
                os.environ["LATEX2HTMLDIR"] = lib_dir
            share_dir = os.path.normpath(os.path.join(root, "..", "share", "lib", "latex2html"))
            if os.path.isdir(share_dir):
                os.environ["LATEX2HTMLPLATDIR"] = share_dir
            self.run(latex2html_bin + " --version 2>&1", env="conanrun")
        else:
            raise Exception("latex2html binary not found in package folder")