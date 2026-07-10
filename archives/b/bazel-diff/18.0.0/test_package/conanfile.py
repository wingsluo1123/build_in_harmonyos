#!/usr/bin/env python3
"""Conan test_package for bazel-diff 18.0.0 — CLI smoke test.

Runs test.sh to verify bazel-diff --help works after installation.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class BazelDiffTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["bazel-diff"]
            bin_dir = os.path.join(dep.package_folder, "bin")

            bash_path = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("bash")
                or "/usr/local/bin/bash"
            )

            self.run(
                f'cd "{self.source_folder}" && '
                f'PATH="{bin_dir}:$PATH" '
                f'"{bash_path}" test.sh',
                env="conanrun"
            )
