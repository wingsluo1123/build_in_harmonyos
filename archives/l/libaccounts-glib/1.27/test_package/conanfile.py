import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibaccountsGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Collect all dependency lib dirs for LD_LIBRARY_PATH
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    lib_dirs.append(lib_dir)
        ld_path = ":".join(lib_dirs)
        os.environ["LD_LIBRARY_PATH"] = ld_path + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        cmd = os.path.join(self.cpp.build.bindirs[0], "test_libaccounts_glib")
        self.run(cmd)
