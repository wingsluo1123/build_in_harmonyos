#!/usr/bin/env python3
"""Consumer test suite for vcf-split 0.1.5-10.

Three independent checks run against the installed package:

1. test_vcf_split.py          — replay the upstream Test/ fixture diff
2. test_vcf_split_workflow.py — complete consumer workflows with semantic
                                assertions on the produced single-sample VCFs
3. test_ohos_binary.py        — OHOS platform conformance of the executable
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class VcfSplitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_vcf_split.py", "test_vcf_split_workflow.py", "test_ohos_binary.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping vcf-split runtime tests because target binaries cannot run")
            return
        package_folder = self.dependencies["vcf-split"].package_folder
        for script_name in (
            "test_vcf_split.py",
            "test_vcf_split_workflow.py",
            "test_ohos_binary.py",
        ):
            script = os.path.join(self.source_folder, script_name)
            self.run(f'"{sys.executable}" "{script}" "{package_folder}"', cwd=self.build_folder, env="conanrun")
