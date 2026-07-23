#!/usr/bin/env python3
"""Conan test_package for openrtsp — verify the binary is packaged correctly."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class OpenrtspTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the openrtsp binary exists and runs
        dep = self.dependencies["openrtsp"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        bin_path = os.path.join(bin_dir, "openRTSP")
        if not os.path.exists(bin_path):
            raise Exception(f"openRTSP binary not found at {bin_path}")
        self.output.info(f"openRTSP binary found at {bin_path}")
        # Run the binary with conanrun environment and verify usage output.
        # openRTSP without args exits 1 with usage text (exit code != 0),
        # so capture the output and check for "Usage:" rather than relying
        # on exit code alone.
        output = self.run(f"{bin_path} 2>&1", ignore_errors=True, env="conanrun", stdout=True)
        if "Usage:" not in output:
            raise Exception(
                f"openRTSP output did not contain expected 'Usage:' text. "
                f"Output: {output[:500]}"
            )
        self.output.info("openRTSP executed successfully with expected usage output")
