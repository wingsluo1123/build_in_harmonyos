import os

from conan import ConanFile
from conan.tools.build import can_run


class MpbTestConan(ConanFile):
    """Consumer test for the mpb CLI/package.

    Runs test.sh which invokes the installed `mpb` binary on a real 2D
    photonic-crystal control file and asserts the computed eigenfrequencies
    against the values published by the upstream `examples/check.ctl`
    self-test (functional check, not a smoke/`--version`-only shell).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
