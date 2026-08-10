import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibaccountsQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2")
        self.requires("glib/2.84.0")
        self.requires("libaccounts-glib/1.27")

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
        old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ld_path + (":" + old_ld if old_ld else "")

        cmd = os.path.join(self.cpp.build.bindirs[0], "test_libaccounts_qt")
        self.run(cmd)
