import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies["sra-sdk"]
        bindir = pkg.cpp_info.bindirs[0]
        libdir = pkg.cpp_info.libdirs[0]

        self.run(os.path.join(self.build_folder, "test-ngs-api"))
        self.run(f'"{bindir}/fasterq-dump" --version')
        self.run(f'"{bindir}/vdb-dump" --version')
        self.run(f'"{bindir}/vdb-config" -f')
        self.run(f'sh "{os.path.join(self.source_folder, "test_ohos.sh")}" '
                 f'"{bindir}" "{libdir}"')
