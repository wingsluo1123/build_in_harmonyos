import os

from conan import ConanFile
from conan.tools.files import save


class TestPerlParamsValidate(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Ensure blib structure is available
        pass

    def test(self):
        # Find the perl binary
        perl_bin = os.environ.get("PERL", "perl")
        test_script = os.path.join(self.source_folder, "test.pl")

        # Run the test script
        self.run(f'{perl_bin} {test_script}', env="conanrun")
