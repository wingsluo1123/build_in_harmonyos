from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy
import os


class CBlosc2Conan(ConanFile):
    name = "c-blosc2"
    version = "3.2.3"
    description = "Fast, compressed, persistent binary data store library for C"
    license = "BSD-3-Clause"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://www.blosc.org"
    topics = ("compression", "binary", "persistent", "blosc")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def requirements(self):
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.7")
        self.requires("zlib-ng-compat/2.3.3")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_FUZZERS"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_PLUGINS"] = False
        tc.variables["PREFER_EXTERNAL_LZ4"] = True
        tc.variables["PREFER_EXTERNAL_ZLIB"] = True
        tc.variables["PREFER_EXTERNAL_ZSTD"] = True
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["blosc2"]
