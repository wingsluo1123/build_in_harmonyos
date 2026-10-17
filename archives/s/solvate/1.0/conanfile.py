import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SolvateConan(ConanFile):
    name = "solvate"
    version = "1.0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "LicenseRef-solvate-no-fee"
    homepage = "https://www.mpibpc.mpg.de/home/grubmueller/downloads/solvate/"
    description = "Construct explicit solvent shells around molecular structures"
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src/solvate_1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], destination="..", strip_root=False)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SOLVATE_SOURCE_DIR"] = self.source_folder.replace(os.sep, "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.export_sources_folder)
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
