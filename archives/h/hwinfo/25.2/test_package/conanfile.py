import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HwinfoTestConan(ConanFile):
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
        # R34: Test must actually exercise the package
        # Run the hwinfo binary from the installed package
        pkg = self.dependencies["hwinfo"].package_folder
        lib_dir = os.path.join(pkg, "lib")
        bin_dir = os.path.join(pkg, "bin")
        uuid_so = glob.glob("/data/service/hnp/**/libuuid.so*", recursive=True)
        uuid_dir = os.path.dirname(uuid_so[0]) if uuid_so else ""
        extra_ld = ":".join(filter(None, [lib_dir, uuid_dir]))
        os.environ["LD_LIBRARY_PATH"] = extra_ld + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        hwinfo_bin = os.path.join(bin_dir, "hwinfo")
        self.run(f'"{hwinfo_bin}" --version')
