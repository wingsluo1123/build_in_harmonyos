#!/usr/bin/env python3
"""Conan consumer test — polly 22.1.8 (LLVM Polly pass plugin).

Delegates the real assertion to test_polly.py (a .py test source, satisfying
L0c), which loads the packaged LLVMPolly.so via the packaged opt and verifies
a SCoP is detected. This is the专项验证 covering the adaptation patch
(config.guess stub + Platform/HarmonyOS) and the core consumer path.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PollyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["polly"].package_folder
        test_py = os.path.join(self.source_folder, "test_polly.py")
        if not os.path.isfile(test_py):
            raise ConanException("test_polly.py not found: {}".format(test_py))
        # Run the packaged-consumer assertion: opt loads LLVMPolly.so and
        # detects the SCoP in test_polly.ll. Non-zero exit = test failure.
        self.run('"{}" "{}" "{}"'.format(sys.executable, test_py, pkg), env="conanrun")
