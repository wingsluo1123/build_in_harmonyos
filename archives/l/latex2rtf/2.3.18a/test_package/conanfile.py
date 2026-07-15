import os

from conan import ConanFile


class Latex2RtfTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["latex2rtf"].cpp_info.bindirs[0]
        latex2rtf_bin = os.path.join(bin_dir, "latex2rtf")
        # Get cfg directory
        cfg_dir = os.path.join(os.path.dirname(bin_dir), "share", "latex2rtf", "cfg")
        # Run test.sh with the binary path and cfg dir as arguments
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{latex2rtf_bin}" "{cfg_dir}"', env="conanrun")
