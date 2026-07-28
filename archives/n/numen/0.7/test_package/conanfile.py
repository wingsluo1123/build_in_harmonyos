import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class NumenTestConan(ConanFile):
    """test_package for numen executable — runs test.sh which invokes numen --help."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: cross-compilation guard — target binary cannot run on x86_64 CI worker
        if cross_building(self):
            self.output.warning("Cross-compilation detected, skipping test execution")
            return
        # Use bash wrapper to execute test.sh (Windows compatibility + OHOS requirement)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        self.run(f'{bash} test.sh', env="conanrun")
