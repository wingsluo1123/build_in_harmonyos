#!/usr/bin/env python3
"""Conan test_package for fnt — a shell script font manager.
Verify the binary exists and has correct shebang (HMDFS can't chmod +x)."""
import os
from conan import ConanFile
from conan.tools.build import cross_building


class FntTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        # Get the package folder where fnt was installed
        pkg = self.dependencies["fnt"]
        bin_path = os.path.join(pkg.package_folder, "bin", "fnt")
        # Verify the file exists and has correct content
        self.run(f"test -f {bin_path}", env="conanrun")
        # Verify shebang is correct (patched for OHOS)
        self.run(f"/data/service/hnp/bin/bash -c 'head -1 {bin_path} | grep -q hnp/bin/bash'", env="conanrun")
        # Verify it has HarmonyOS platform support
        self.run(f"/data/service/hnp/bin/bash -c 'grep -q HarmonyOS {bin_path}'", env="conanrun")
        print(f"✅ fnt verified: {bin_path}")