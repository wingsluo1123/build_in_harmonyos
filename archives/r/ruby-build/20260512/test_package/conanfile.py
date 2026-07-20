#!/usr/bin/env python3
"""Conan test_package for ruby-build 20260512 — Shell script test.

Verifies that the ruby-build command is functional after installation.
Runs ruby-build --version and ruby-build --list to verify real functionality.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class RubyBuildTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["ruby-build"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            ruby_build_cmd = os.path.join(bin_dir, "ruby-build")

            # Find bash for executing the scripts
            bash_path = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("bash")
                or "/usr/local/bin/bash"
            )
            bash_dir = os.path.dirname(bash_path)
            full_path = f"{bin_dir}:{bash_dir}"

            # Run test.sh smoke test (source file for CI L0c compliance)
            self.run(
                f'cd "{self.source_folder}" && '
                f'PATH="{full_path}:$PATH" '
                f'"{bash_path}" test.sh',
                env="conanrun"
            )

            # Test 1: ruby-build --version should print version info
            self.run(
                f'PATH="{full_path}:$PATH" "{ruby_build_cmd}" --version',
                env="conanrun"
            )

            # Test 2: ruby-build --list should list available Ruby versions
            self.run(
                f'PATH="{full_path}:$PATH" "{ruby_build_cmd}" --list',
                env="conanrun"
            )
            self.output.info("ruby-build test: PASS (--version + --list)")
