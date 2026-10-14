import os

from conan import ConanFile


class Gem5TestConan(ConanFile):
    """test_package for gem5 — real end-to-end SE simulation smoke test.

    The binary under test is the packaged ``gem5.opt`` itself: test.sh
    compiles a freestanding AArch64 guest with the platform clang and runs
    it on the packaged simulator in syscall-emulation (SE) mode, asserting
    the guest output and the simulator exit status (R34/R53).
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap the
        # test script with bash (the profile provides CONFIG_SHELL).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
