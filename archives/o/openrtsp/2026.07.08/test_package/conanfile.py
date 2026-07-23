#!/usr/bin/env python3
"""Conan test_package for openrtsp — verify the binary is packaged correctly."""
import os

from conan import ConanFile


class OpenrtspTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

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
        # Run the binary to verify it executes (openRTSP without args exits 1
        # with usage text, which is expected behavior, so ignore_errors is used).
        self.run(f"{bin_path} 2>&1", ignore_errors=True, env="conanrun")
        # Verify the binary produced actual output (usage text)
        import subprocess
        result = subprocess.run([bin_path], capture_output=True, text=True)
        output = (result.stdout + result.stderr).strip()
        if not output:
            raise Exception(f"openRTSP binary at {bin_path} produced no output (expected usage text)")
        self.output.info(f"openRTSP executed successfully (usage text: {len(output)} chars)")