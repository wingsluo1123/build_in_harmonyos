from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, get

class HiGHSConan(ConanFile):
    name = "highs"
    version = "1.13.1"
    license = "MIT"
    author = "ERGO-Code"
    url = "https://github.com/ERGO-Code/HiGHS"
    description = "Linear optimization library"
    topics = ("optimization", "solver", "linear-programming")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "CMakeToolchain"
    exports_sources = "patches/*"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["highs"]