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

        # Run the shell-based test script for the actual texi2html conversion test
        test_script = os.path.join(self.source_folder, "test_texi2html.sh")
        assert os.path.isfile(test_script), f"test_texi2html.sh not found at {test_script}"
        # Run the conversion in an explicit writable work dir under the build
        # folder (OHOS CI CWD / /tmp may not be writable).
        work_dir = os.path.join(str(self.build_folder), "texi2html-test-work")
        self.run(
            f'bash "{test_script}" "{texi2html}" "{libintl}" "{self.source_folder}" "{work_dir}"',
            env="conanrun",
        )
        self.output.info("texi2html SUCCESS: test_texi2html.sh passed")

        # Determinism consumer regression: two independent processes on the
        # same multi-node/multi-section input must produce byte-identical HTML
        # (perl hash-order determinism).
        determinism_script = os.path.join(self.source_folder, "test_determinism.sh")
        assert os.path.isfile(determinism_script), f"test_determinism.sh not found at {determinism_script}"
        self.run(
            f'bash "{determinism_script}" "{texi2html}" "{libintl}" "{self.source_folder}" "{work_dir}"',
            env="conanrun",
        )
        self.output.info("texi2html SUCCESS: test_determinism.sh passed")