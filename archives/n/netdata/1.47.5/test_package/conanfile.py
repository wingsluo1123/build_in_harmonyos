import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NetdataTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Find the netdata binary in the package's bindirs
        netdata_bin = None
        for bindir in self.dependencies["netdata"].cpp_info.bindirs:
            for root in [self.dependencies["netdata"].package_folder]:
                candidate = os.path.join(root, bindir, "netdata")
                if os.path.isfile(candidate):
                    netdata_bin = candidate
                    break
            if netdata_bin:
                break

        if not netdata_bin:
            # Fallback: search common locations
            pkg_folder = self.dependencies["netdata"].package_folder
            for dirpath, dirnames, filenames in os.walk(pkg_folder):
                if "netdata" in filenames:
                    netdata_bin = os.path.join(dirpath, "netdata")
                    break

        if not netdata_bin:
            raise Exception("netdata binary not found in package")

        print(f"Found netdata at: {netdata_bin}")
        self.run(f'"{netdata_bin}" -v', env="conanrun")
