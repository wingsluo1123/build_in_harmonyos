#!/usr/bin/env python3
"""test_package — OHOS consumer smoke test for the vdr executable.

`vdr` is a daemon: on this device there is neither a DVB adapter
(/dev/dvb and /sys/class/dvb are both absent) nor a video directory, so the
only meaningful consumer-side checks are the ones that exit before device
probing, plus the documented failure path for a missing video directory.
"""

import os

from conan import ConanFile


class VdrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "vdr")
        script = os.path.join(self.recipe_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" "{script}" "{executable}"', env="conanrun")
