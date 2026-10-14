import os

from conan import ConanFile


class SouffleTestConan(ConanFile):
    """test_package for the souffle application + library package.

    Runs test.sh which invokes the installed `souffle` binary end-to-end
    (--version plus a real Datalog program producing and comparing CSV output).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: the shell running conan cannot necessarily execute ELF binaries
        # directly, so wrap the test script in a shell that can.  Prefer the
        # HMBS-injected SHELL/CONFIG_SHELL; never hardcode a HNP bash path.
        bash = (
            os.environ.get("CONFIG_SHELL")
            or os.environ.get("SHELL")
            or "/system/bin/sh"
        )
        self.run(f"{bash} test.sh", env="conanrun")
