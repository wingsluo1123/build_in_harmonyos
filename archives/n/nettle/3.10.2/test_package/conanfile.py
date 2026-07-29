import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class NettleTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    win_bash = True

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("gmp/6.3.0")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.tool_requires("msys2/cci.latest")

    def layout(self):
        cmake_layout(self)

    def build(self):
        if self.settings.os == "Windows":
            nettle = self.dependencies["nettle"].package_folder
            gmp = self.dependencies["gmp"].package_folder
            source = self._unix_path(os.path.join(self.source_folder, "test_nettle.c"))
            output = self._unix_path(os.path.join(self.build_folder, "test_nettle.exe"))
            command = (
                f'gcc -I"{self._unix_path(os.path.join(nettle, "include"))}" '
                f'-I"{self._unix_path(os.path.join(gmp, "include"))}" '
                f'"{source}" '
                f'-L"{self._unix_path(os.path.join(nettle, "lib"))}" '
                f'-L"{self._unix_path(os.path.join(gmp, "lib"))}" '
                f'-lhogweed -lnettle -lgmp -lm -o "{output}"'
            )
            self.run(command)
            return

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            name = "test_nettle.exe" if self.settings.os == "Windows" else "test_nettle"
            if self.settings.os == "Windows":
                cmd = self._unix_path(os.path.join(self.build_folder, name))
            else:
                cmd = os.path.join(self.cpp.build.bindir, name)
            self.run(cmd, env="conanrun")

    def _unix_path(self, path):
        return path.replace("\\", "/")
