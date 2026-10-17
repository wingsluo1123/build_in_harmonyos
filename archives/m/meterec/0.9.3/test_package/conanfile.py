import os
import shutil

from conan import ConanFile


class MeterecTestConan(ConanFile):
    """test_package for the meterec executables — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly
        # in all contexts; wrap binary execution in bash. On-device bash
        # lives at /data/service/hnp/bin/bash; local verification uses the
        # host bash on PATH (mirrors the m1ddc pattern, hardened for
        # off-device runs).
        bash = (
            shutil.which("bash")
            or os.environ.get("CONFIG_SHELL")
            or "/data/service/hnp/bin/bash"
        )
        self.run(f"{bash} test.sh", env="conanrun")
