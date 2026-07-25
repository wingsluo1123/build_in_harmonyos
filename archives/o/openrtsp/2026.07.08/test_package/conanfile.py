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
        # Run test_openrtsp.sh with conanrun environment (sets LD_LIBRARY_PATH for openssl)
        script_path = os.path.join(self.source_folder, "test_openrtsp.sh")
        self.run(f"/system/bin/sh {script_path} {bin_path}", env="conanrun")
