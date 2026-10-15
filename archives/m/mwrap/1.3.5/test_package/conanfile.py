#!/usr/bin/env python3
"""Conan test_package — mwrap 1.3.5.

Runs two real shell test scripts against the installed package
(R34: the test must drive the package's own binary, not just print
a string):

  1. test_mwrap.sh          — consumer smoke: mwrap runs on the target,
                              generates a MEX gateway (.cc) and a MATLAB
                              stub (.m) from a real .mw input, verifies
                              the generated code content.
  2. ohos_specific_test.sh  — ★鸿蒙新增消费者用例: end-to-end generation
                              with a private TMPDIR, -cppcomplex support
                              code, deterministic re-generation, and the
                              missing-input error path, all executed on
                              the real OHOS platform.
"""
import os

from conan import ConanFile


class MwrapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies["mwrap"].package_folder, "bin")
        bash = os.environ.get("CONFIG_SHELL", "bash")

        # 1) consumer smoke test
        self.run(f'{bash} "{os.path.join(self.source_folder, "test_mwrap.sh")}" '
                 f'"{bindir}" "{os.path.join(self.build_folder, "consumer")}"',
                 env="conanrun")

        # 2) HarmonyOS-specific consumer test
        work = os.path.join(self.build_folder, "ohos")
        log = os.path.join(self.build_folder, "ohos-test.log")
        self.run(f'{bash} "{os.path.join(self.source_folder, "ohos_specific_test.sh")}" '
                 f'"{bindir}" "{work}" "{log}"',
                 env="conanrun")
