import os
import shlex
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SympolConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG"] = "-Wl,-rpath,"
            tc.variables["CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP"] = ":"
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["sympol"].package_folder
        binary = os.path.join(package, "bin", "sympol")
        if not os.path.isfile(binary):
            raise RuntimeError("installed SymPol executable missing")
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "consumer"), env="conanrun")
            self.run(shlex.join([sys.executable,
                                 os.path.join(self.source_folder, "test_sympol.py"),
                                 binary, os.path.join(self.build_folder, "harmony-e2e")]),
                     env="conanrun")
