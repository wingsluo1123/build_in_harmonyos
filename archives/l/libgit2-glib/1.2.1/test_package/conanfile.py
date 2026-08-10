import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libgit2GlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0")
        self.requires("libgit2/1.9.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Verify the test binary was built successfully (compilation + linking)
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libgit2_glib")
        assert os.path.exists(binary), f"Test binary not found: {binary}"
        self.output.info("Test binary built and linked successfully")
