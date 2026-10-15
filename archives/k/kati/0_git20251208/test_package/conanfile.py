#!/usr/bin/env python3
"""Conan test_package: kati/0_git20251208 consumer verification.

Runs the installed `ckati` as a real build interpreter (see test.sh):
a Makefile exercising pattern rules / automatic vars / text functions /
phony targets produces real artifacts, content is asserted exactly, and
a second incremental run must not re-execute the recipe (kati's core
regen-detection purpose). The differential testcase suite (296 cases)
runs in build() via tests/run_testcases.py — see MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class KatiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        # OHOS 真机 bash 路径与 test_package-executable 模板一致
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_sh}"', env="conanrun")
