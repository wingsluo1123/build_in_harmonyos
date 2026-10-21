from pathlib import Path
import shlex
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

class Consumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = Path(self.dependencies["asio"].package_folder)
        for name in ("asio.hpp", "asio/version.hpp", "asio/detail/impl/epoll_reactor.ipp"):
            if not (package / "include" / name).is_file():
                raise RuntimeError("Installed Asio header absent: " + name)
        if can_run(self):
            binary = Path(self.build_folder) / self.cpp.build.bindirs[0] / "consumer"
            self.run(shlex.join([sys.executable, str(Path(self.source_folder) / "run.py"), str(binary)]), env="conanrun")
