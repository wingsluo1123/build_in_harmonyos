import os

from conan import ConanFile


class MdfriedTestConan(ConanFile):
    """test_package for mdfried executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: settings.os check uses in ("Linux", "OHOS")
        # Use sh (mksh on OHOS) since bash may not be installed
        if self.settings.os in ("Linux", "OHOS"):
            sh = os.environ.get("CONFIG_SHELL", "sh")
            self.run(f"{sh} test.sh", env="conanrun")
