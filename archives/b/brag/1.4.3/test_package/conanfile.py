import os

from conan import ConanFile
from conan.tools.files import load


class BragTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must substantively depend on the tested package
        # brag is a Tcl script; verify it is packaged correctly
        brag_path = os.path.join(self.dependencies["brag"].package_folder, "bin", "brag")
        assert os.path.isfile(brag_path), f"brag not found at {brag_path}"
        # Verify brag is a tcl script with tclsh reference
        content = load(self, brag_path)
        assert "tclsh" in content, "brag script does not contain tclsh reference"
        self.output.info("brag script verified: file exists and contains tclsh reference")
        # Verify brag is executable (R34: substantive test)
        self.run(f"test -x {brag_path}", env="conanrun")
