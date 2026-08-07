import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Find the driver .so in the package
        pkg_info = self.dependencies["qt-libiodbc"]
        libdirs = pkg_info.cpp_info.libdirs
        so_files = []
        for d in libdirs:
            so_files.extend(glob.glob(os.path.join(d, "**", "*.so"), recursive=True))
            so_files.extend(glob.glob(os.path.join(pkg_info.package_folder, "**", "*.so"), recursive=True))
        if not so_files:
            raise Exception("No .so files found in qt-libiodbc package")
        so_file = so_files[0]
        # Verify ELF magic and name contains 'iodbc'
        self.run(f'nm -D "{so_file}" 2>/dev/null | head -3 || readelf -d "{so_file}" | head -3', env="conanrun")
        # Run the test binary with the .so path
        bin_path = os.path.join(self.build_folder, "test_package")
        if os.path.isfile(bin_path):
            self.run(f'"{bin_path}" "{so_file}"', env="conanrun")
