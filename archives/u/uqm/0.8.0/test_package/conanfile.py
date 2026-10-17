#!/usr/bin/env python3
"""test_package for uqm — runs the installed `uqm` launcher.

Consumer verification: invoke the binary the way an installed user would
(through the `bin/uqm` launcher that supplies --contentdir) and check
observable output + exit codes.
"""
import os

from conan import ConanFile


class UqmTestConan(ConanFile):
    """test_package for uqm — runs test.sh which invokes the uqm launcher."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
