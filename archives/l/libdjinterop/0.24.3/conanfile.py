from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class LibdjinteropConan(ConanFile):
    name = "libdjinterop"
    version = "0.24.3"
    description = "C++ library for accessing DJ database formats (Engine Prime, Rekordbox, Serato)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/xsco/libdjinterop"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

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

    def package_info(self):
        self.cpp_info.libs = ["djinterop"]

    def requirements(self):
        self.requires("zlib/1.2.13")
