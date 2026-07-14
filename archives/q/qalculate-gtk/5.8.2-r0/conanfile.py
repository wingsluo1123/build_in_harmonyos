from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get


class QalculateGtkRecipe(ConanFile):
    name = "qalculate-gtk"
    version = "5.8.2-r0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    description = "Qalculate GTK frontend"
    topics = ("calculator", "gtk", "qt")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
