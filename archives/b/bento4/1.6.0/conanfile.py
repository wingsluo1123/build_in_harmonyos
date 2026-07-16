from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get
import os

class Bento4Conan(ConanFile):
    name = "bento4"
    version = "1.6.0"
    license = "MIT"
    author = "axiomatic-systems"
    url = "https://github.com/axiomatic-systems/Bento4"
    description = "MP4 library and tools"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "CMakeToolchain"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "*.h", src=os.path.join(self.source_folder, "Source"), dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "Source"), dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["ap4"]