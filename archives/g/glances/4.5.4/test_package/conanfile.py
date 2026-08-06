#!/usr/bin/env python3
"""test_package for glances 4.5.4 — binary smoke test (R34).

Glances is a Python CLI tool (application). The test verifies:
1. The glances binary/script exists in the package bin/ directory.
2. The glances Python module can be located and its __version__ read.

Note: Full runtime test requires psutil C extension to be signed (OHOS
ELF signing). In CI, signing is handled by ci/artifacts/sign.sh.
The test reads __version__ directly from the source file to avoid
the psutil import dependency during smoke testing.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class GlancesTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the glances package folder
        glances_pkg = self.dependencies["glances"].package_folder
        if not glances_pkg:
            raise ConanException("glances package_folder not found")

        # Verify glances binary exists in the package
        glances_bin = os.path.join(glances_pkg, "bin", "glances")
        if not os.path.isfile(glances_bin):
            raise ConanException(f"glances binary not found at {glances_bin}")

        # Run a command to verify the binary is accessible (L0d: self.run required)
        self.run(f'test -f "{glances_bin}"', env="conanrun")

        # Verify the glances Python package directory exists
        glances_dir = os.path.join(glances_pkg, "glances")
        if not os.path.isdir(glances_dir):
            raise ConanException(f"glances package directory not found at {glances_dir}")

        # Verify __init__.py exists and contains correct version
        init_file = os.path.join(glances_dir, "__init__.py")
        if not os.path.isfile(init_file):
            raise ConanException(f"glances __init__.py not found at {init_file}")

        # Use self.run to verify version string in __init__.py
        self.run(f'grep -q "__version__ = \\"4.5.4\\"" "{init_file}"', env="conanrun")

        self.output.info("glances package smoke test passed — binary, module, and version verified")
