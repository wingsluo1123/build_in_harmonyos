#!/usr/bin/env python3
"""Conan test_package for texi2html application.

Tests that texi2html can convert a minimal Texinfo document to HTML.
"""
import os
from conan import ConanFile
from conan.tools.files import chdir


class Texi2HtmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["texi2html"]
        package_folder = str(dep.package_folder)
        texi2html = os.path.join(package_folder, "bin", "texi2html")
        assert os.path.isfile(texi2html), f"texi2html binary not found at {texi2html}"
        libintl = os.path.join(package_folder, "share", "texi2html", "lib", "libintl-perl", "lib")
        assert os.path.isdir(libintl), f"bundled libintl-perl not found at {libintl}"

        # Test texi2html by converting the static sample.texi from the repo
        sample_texi = os.path.join(self.source_folder, "sample.texi")
        assert os.path.isfile(sample_texi), f"sample.texi not found at {sample_texi}"
        with chdir(self, self.source_folder):
            self.run(f'PERL5LIB="{libintl}" timeout 30 "texi2html" --no-validate sample.texi 2>&1', env="conanrun")
        sample_html = os.path.join(self.source_folder, "sample.html")
        assert os.path.isfile(sample_html), f"texi2html did not generate sample.html"
        with open(sample_html, "r") as f:
            content = f.read()
        assert "Hello from texi2html" in content, (
            f"sample.html missing expected content, got {len(content)} bytes"
        )
        self.output.info(f"texi2html SUCCESS: sample.html generated ({os.path.getsize(sample_html)} bytes, contains 'Hello from texi2html')")