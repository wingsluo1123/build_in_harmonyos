#!/usr/bin/env python3
"""Conan test_package for helm 3.19.0 — L1 smoke test.

Tests that the helm binary can be executed and reports its version.
Uses test_helm.sh as the test source file (CI L0c gate requirement).
"""
import os

from conan import ConanFile


class HelmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the helm binary in the package
        helm_bin = os.path.join(self.dependencies["helm"].package_folder, "bin", "helm")
        self.output.info(f"Testing helm binary at: {helm_bin}")
        # Run test_helm.sh which tests helm version + help + completion
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test_helm.sh "{helm_bin}"', env="conanrun")
