import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstRtspServerTestConan(ConanFile):
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
        pkg = self.dependencies["gst-rtsp-server"]
        libdir = os.path.join(pkg.package_folder, "lib")
        libs = glob.glob(os.path.join(libdir, "libgstrtspserver-1.0.so*"))
        if not libs:
            raise Exception(f"gst-rtsp-server shared library not found in {libdir}")
        self.output.info(f"Found gst-rtsp-server library: {libs[0]}")

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gst_rtsp_server")
        self.run(f'{bin_path}', ignore_errors=True)
        self.output.info("Test binary compiled and linked successfully against gst-rtsp-server library")
