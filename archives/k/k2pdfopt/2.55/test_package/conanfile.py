#!/usr/bin/env python3
"""Conan test_package — k2pdfopt 2.55 (consumer-view L1 test).

Runs the packaged k2pdfopt executable end-to-end: converts the embedded
one-page test PDF (MuPDF render -> k2pdfopt page optimization -> PDF out)
and verifies the output file is a real PDF.
"""
import os

from conan import ConanFile


class K2pdfoptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_root = self.dependencies[self.tested_reference_str].cpp_info.bindir
        exe = os.path.join(bin_root, "k2pdfopt")
        here = os.path.dirname(__file__)
        script = os.path.join(here, "run_test.sh")
        self.run(f'"{script}" "{exe}" "{os.path.join(here, "test.pdf")}"',
                 env="conanrun")
