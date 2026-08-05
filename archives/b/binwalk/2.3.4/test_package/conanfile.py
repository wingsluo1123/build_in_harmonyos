"""test_package for binwalk 2.3.4 — smoke test (R34)."""
from conan import ConanFile
from conan.errors import ConanException


class BinwalkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify binwalk module can be imported and runs correctly
        ret = self.run(
            'python3 -c "import binwalk; print(binwalk.__version__)"',
            env="conanrun",
        )
        if ret != 0:
            raise ConanException(f"import binwalk failed with exit code {ret}")
