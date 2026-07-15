from conan import ConanFile
from conan.tools.files import get, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CLI11Conan(ConanFile):
    name = "cli11"
    version = "2.6.2"
    description = "CLI11 is a command line parser for C++11 and beyond"
    license = "BSD-3-Clause"
    homepage = "https://github.com/CLIUtils/CLI11"
    url = ""

    package_type = "header-library"

    settings = "os", "compiler", "arch", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CLI11_BUILD_TESTS"] = "OFF"
        tc.variables["CLI11_BUILD_EXAMPLES"] = "OFF"
        tc.variables["CLI11_BUILD_DOCS"] = "OFF"
        tc.variables["CLI11_PRECOMPILED"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "CLI11")
        self.cpp_info.set_property("cmake_target_name", "CLI11::CLI11")
        self.cpp_info.set_property("pkg_config_name", "CLI11")
