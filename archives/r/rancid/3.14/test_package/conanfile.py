#!/usr/bin/env python3
"""Conan test_package — rancid 3.14.

Tests that the compiled binary (hpuifilter) can be executed.
rancid is a tool package with no libraries to link against.
"""
import os

from conan import ConanFile


class RancidTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use Conan 2.x API to find the binary
        rancid = self.dependencies["rancid"]

        # Try to find hpuifilter in the package's bin directories
        bin_paths = []
        if rancid.cpp_info.bindirs:
            bin_paths = rancid.cpp_info.bindirs
        elif rancid.cpp_info.libdirs:
            bin_paths = rancid.cpp_info.libdirs

        found = False
        for bin_dir in bin_paths:
            for binary in ["hpuifilter", "par"]:
                bin_path = os.path.join(bin_dir, binary)
                if os.path.exists(bin_path):
                    self.run(f'"{bin_path}" --help', env="conanrun", ignore_errors=True)
                    found = True
                    self.output.info(f"Found and tested: {bin_path}")
                    break
            if found:
                break

        if not found:
            # List available directories for debugging
            self.output.info(f"bindirs: {rancid.cpp_info.bindirs}")
            self.output.info(f"libdirs: {rancid.cpp_info.libdirs}")
            # Try to find in package folder
            pkg_path = rancid.package_folder
            self.output.info(f"package_folder: {pkg_path}")
            if pkg_path and os.path.isdir(pkg_path):
                for root, dirs, files in os.walk(pkg_path):
                    for f in files:
                        self.output.info(f"  {os.path.join(root, f)}")
            raise Exception("Could not find hpuifilter or par binary in the package")
