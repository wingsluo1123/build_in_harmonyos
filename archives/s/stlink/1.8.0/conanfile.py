from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class StlinkConan(ConanFile):
    name = "stlink"
    version = "1.8.0"
    description = "STM32 MCU programmer toolkit (st-flash, st-info, st-util)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/stlink-org/stlink"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
