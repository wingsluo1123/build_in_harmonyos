#!/usr/bin/env python3
"""Conan test_package for ragel 6.10.

Verifies that the ragel binary is functional after installation:
  1. ragel --version prints version info
  2. ragel compiles a simple state machine .rl file to C code
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class RagelTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get the bin directory from the dependency package
            dep = self.dependencies["ragel"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            ragel_cmd = os.path.join(bin_dir, "ragel")

            # Test 1: ragel --version
            self.run(f'"{ragel_cmd}" --version', env="conanrun")

            # Test 2: compile a simple state machine to C
            rl_file = os.path.join(self.source_folder, "src", "test_simple.rl")
            output_file = os.path.join(self.build_folder, "test_simple.c")
            self.run(
                f'"{ragel_cmd}" -C -o "{output_file}" "{rl_file}"',
                env="conanrun"
            )
            # Verify the output C file was generated and contains expected code
            if not os.path.isfile(output_file):
                raise Exception(f"ragel did not generate output file: {output_file}")
            with open(output_file, "r") as f:
                content = f.read()
            if "ragel" not in content.lower() and "fsm" not in content.lower() and "state" not in content.lower():
                raise Exception("ragel output does not contain expected state machine code")
            self.output.info("ragel test: PASS (version + compilation)")
