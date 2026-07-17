#!/usr/bin/env python3
"""Conan test_package for texi2html application."""
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

        # Test texi2html by creating a minimal texinfo document and converting it
        test_file = os.path.join(self.source_folder, "sample.texi")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("\\input texinfo\n@setfilename sample.info\n@node Top\n@top Sample\nHello from texi2html.\n@bye\n")
        with chdir(self, self.source_folder):
            self.run(f'PERL5LIB="{libintl}" "texi2html" --no-validate sample.texi 2>&1; RC=$?; if [ -f sample.html ]; then echo "texi2html OK: sample.html generated"; exit 0; else echo "texi2html FAILED: no sample.html"; exit $RC; fi', env="conanrun")