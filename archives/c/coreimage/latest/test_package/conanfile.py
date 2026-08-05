import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class CoreimageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("libcprime/latest")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"]
        qtbase_root = qtbase.package_folder
        tc.variables["Qt6_DIR"] = f"{qtbase_root}/lib/cmake/Qt6"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("qtbase", "cmake_file_name", "Qt6")
        deps.set_property("qtbase", "cmake_target_name", "Qt6::Core")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_coreimage")
        self.run(test_exe, env="conanrun")
