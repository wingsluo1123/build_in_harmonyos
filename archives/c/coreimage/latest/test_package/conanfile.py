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
        # R34: Execute the coreimage binary to verify the package was built correctly
        # coreimage is a GUI app, --help should print usage and exit
        coreimage_pkg = self.dependencies["coreimage"].package_folder
        coreimage_exe = os.path.join(coreimage_pkg, "bin", "coreimage")
        self.run(f'"{coreimage_exe}" --help', env="conanrun")
