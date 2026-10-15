import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Krb5ServerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # 链接 libkrb5 等服务端库集，验证库可用
            bin_path = os.path.join(self.cpp.build.bindir, "test_krb5server")
            self.run(bin_path, env="conanrun")
            # 真实调用服务端工具 kdb5_util：创建/查询 KDB
            script = os.path.join(self.source_folder, "test_krb5server.sh")
            self.run(f"sh {script}", env="conanrun")
