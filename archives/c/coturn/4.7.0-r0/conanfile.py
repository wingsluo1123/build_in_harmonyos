from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class CoturnRecipe(ConanFile):
    name = "coturn"
    version = "4.7.0-r0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = ()
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "BSD-3-Clause"
    description = "TURN and STUN server"
    topics = ("turn", "stun", "network")

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-static",
            "--enable-shared",
        ])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
