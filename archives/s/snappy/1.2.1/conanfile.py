"""Conan recipe — snappy 1.2.1 (Google Snappy compression library).

Snappy is a fast compression/decompression library developed by Google.
It aims for very high speeds and reasonable compression ratios.
Source: Google Snappy release-1.2.1 tag on GitHub
License: BSD-3-Clause

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
R33: compiler flags from Conan Toolchain, no bare shell variables
R34: test_package calls snappy API
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class SnappyConan(ConanFile):
    name = "snappy"
    version = "1.2.1"
    description = "Google Snappy — a fast compression/decompression library"
    license = "BSD-3-Clause"
    homepage = "https://google.github.io/snappy/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos"):
            raise ConanInvalidConfiguration(
                f"snappy does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SNAPPY_BUILD_TESTS"] = False
        tc.variables["SNAPPY_BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst="licenses")

    def package_info(self):
        self.cpp_info.libs = ["snappy"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("c++")
