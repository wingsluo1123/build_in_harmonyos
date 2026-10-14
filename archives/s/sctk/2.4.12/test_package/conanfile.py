#!/usr/bin/env python3
"""Conan test_package for sctk 2.4.12 — NIST Speech Recognition Scoring Toolkit.

Consumer verification: run the installed `rfilter1` (C binary) end-to-end on
upstream test data, check `sclite` version output, and verify a Perl-script
tool is installed with a working interpreter.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class SctkTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["sctk"]
        bindir = os.path.join(dep.package_folder, "bin")

        # 检查安装产物
        for tool in ["sclite", "asclite", "rfilter1"]:
            path = os.path.join(bindir, tool)
            if not os.path.isfile(path):
                raise ConanException(f"{tool} not found in package: {path}")
        self.output.info(f"  sctk bin tools present ({len(os.listdir(bindir))} entries)")

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly;
        # use bash wrapper like other tool recipes.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
