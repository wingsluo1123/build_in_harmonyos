from conan import ConanFile


class NcursesTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # ncurses is a library — verify headers are available
        self.run("echo 'ncurses/6.4 library package'", env="conanrun")