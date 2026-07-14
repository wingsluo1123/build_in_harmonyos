from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class CrunchRecipe(ConanFile):
    name = "crunch"
    version = "3.6"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    description = "Password wordlist generator"
    topics = ("security", "wordlist", "password")

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
