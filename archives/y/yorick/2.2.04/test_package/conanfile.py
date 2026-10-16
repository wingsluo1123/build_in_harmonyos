#!/usr/bin/env python3
"""test_package for yorick — invokes the installed `yorick` interpreter.

Consumer verification: run the real yorick binary in batch mode on test.i,
which exercises core interpreter arithmetic, array reductions and matrix
indexing and prints a success marker; the shell wrapper asserts exit code 0
and the marker (real output, not a stub).
"""
import os

from conan import ConanFile


class YorickTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
