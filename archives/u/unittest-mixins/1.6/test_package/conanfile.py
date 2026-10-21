#!/usr/bin/env python3
"""Custom Python consumer and separate HarmonyOS platform verification."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class UnittestMixinsTest(ConanFile):
    settings = 'os', 'arch', 'compiler', 'build_type'
    test_type = 'explicit'
    generators = 'VirtualRunEnv'

    def requirements(self):
        self.requires(self.tested_reference_str, headers=False, libs=False, run=True)

    def test(self):
        if not can_run(self):
            self.output.warning('Target execution unavailable; native validation is still required')
            return
        environment = Environment()
        environment.define('PYTHONDONTWRITEBYTECODE', '1')
        with environment.vars(self).apply():
            consumer = os.path.join(self.source_folder, 'test_consumer.py')
            self.run(f'"{sys.executable}" "{consumer}"', env='conanrun')
            if self.settings.os == 'OHOS':
                platform = os.path.join(self.source_folder, 'test_harmonyos_hmdfs.py')
                self.run(f'"{sys.executable}" "{platform}"', env='conanrun')
