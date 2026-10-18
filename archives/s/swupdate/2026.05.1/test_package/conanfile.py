import os

from conan import ConanFile
from conan.tools.build import can_run


class SwupdateTestConan(ConanFile):
    """Consumer test for the swupdate application package.

    Runs test.sh with the installed bin/ on PATH and the dependency
    libraries on LD_LIBRARY_PATH.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} {os.path.join(self.source_folder, 'test.sh')}",
                 env="conanrun")
