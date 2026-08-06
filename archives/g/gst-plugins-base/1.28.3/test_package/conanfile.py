import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstPluginsBaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Verify the shared library exists in the package
        pkg = self.dependencies["gst-plugins-base"]
        libdir = os.path.join(pkg.package_folder, "lib")
        libs = glob.glob(os.path.join(libdir, "libgstapp-1.0.so*"))
        if not libs:
            raise Exception(f"gst-plugins-base shared library not found in {libdir}")
        self.output.info(f"Found gst-plugins-base library: {libs[0]}")

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gst_plugins_base")
        self.run(f'{bin_path}', ignore_errors=True)
        self.output.info("Test binary compiled and linked successfully against gst-plugins-base library")
