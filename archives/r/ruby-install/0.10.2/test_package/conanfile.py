#!/usr/bin/env python3
"""Conan test_package for ruby-install 0.10.2 — Shell script test.

Verifies that the ruby-install command is functional after installation.
Runs --version and --help to verify the script is correctly installed.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class RubyInstallTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get the bin directory from the dependency package
            dep = self.dependencies["ruby-install"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            ruby_install_cmd = os.path.join(bin_dir, "ruby-install")

            # Find bash for executing the scripts (OHOS may not have bash in default PATH)
            bash_path = (
                shutil.which("bash")
                or os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or "/data/service/hnp/bin/bash"
            )
            bash_dir = os.path.dirname(bash_path)

            # Set up PATH so ruby-install can find its share/ scripts and bash
            share_dir = os.path.join(dep.package_folder, "share")
            full_path = f"{bin_dir}:{bash_dir}:/bin:/usr/bin"

            # Run test.sh smoke test (source file for CI L0c compliance)
            # Use bash explicitly to run test.sh
            self.run(
                f'cd "{self.source_folder}" && '
                f'export PATH="{full_path}:$PATH" && '
                f'export RUBY_INSTALL_CMD="{ruby_install_cmd}" && '
                f'export SHARE_DIR="{share_dir}" && '
                f'"{bash_path}" test.sh "{ruby_install_cmd}"',
                env="conanrun"
            )
