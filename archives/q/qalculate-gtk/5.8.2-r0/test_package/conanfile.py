from conan import ConanFile


class QalculateGtkTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("qalculate-gtk --help", env="conanrun")
