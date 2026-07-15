from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class HackrfConan(ConanFile):
    name = "hackrf"
    version = "2024.02.1"
    description = "HackRF Software Defined Radio tools (hackrf_info, hackrf_transfer)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/greatscottgadgets/hackrf"
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
