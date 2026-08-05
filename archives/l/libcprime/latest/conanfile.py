from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
import os


class LibcprimeConan(ConanFile):
    name = "libcprime"
    version = "latest"
    description = "A library for CoreApps family"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rahmanshaber/libcprime"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # qtbase uses cmake_find_mode=none, set CMAKE_PREFIX_PATH so CMake finds Qt6Config.cmake
        qtbase = self.dependencies["qtbase"]
        qtbase_root = qtbase.package_folder
        tc.variables["CMAKE_PREFIX_PATH"] = qtbase_root
        tc.generate()

        deps = CMakeDeps(self)
        # qtbase provides Qt6Config.cmake (not qtbase-config.cmake), so map the cmake file name
        deps.set_property("qtbase", "cmake_file_name", "Qt6")
        deps.set_property("qtbase", "cmake_target_name", "Qt6::Core")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cprime"]
        self.cpp_info.set_property("cmake_file_name", "cprime")
        self.cpp_info.set_property("cmake_target_name", "cprime::cprime")
        self.cpp_info.includedirs = ["include"]
