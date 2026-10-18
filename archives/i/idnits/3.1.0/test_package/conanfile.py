from conan import ConanFile


class IdnitsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("/system/bin/sh test_idnits.sh", env="conanrun")
