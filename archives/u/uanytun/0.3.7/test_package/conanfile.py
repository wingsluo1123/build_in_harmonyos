import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class UanytunTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34：真实调用被测包 —— 直接跑打包出来的 uanytun 二进制，
        # 再运行 test.c 里经 PATH 定位二进制的独立验证（版本 + 用法输出）。
        if not can_run(self):
            self.output.info("cross-building: test.c 只编译不执行，"
                             "二进制执行留给 CI/设备原生运行")
            return
        self.run("uanytun -v", env="conanrun")
        exe = os.path.join(self.build_folder, "test_uanytun")
        self.run(f'"{exe}"', env="conanrun")
