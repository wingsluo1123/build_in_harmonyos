#!/usr/bin/env python3
"""libhl ae3e64484b 消费者测试（Conan L1）。

CI 通过 `conan create` 自动调用：构建 test.c 并链接已安装的 libhl，
断言 ht_*（哈希表）与 list_*（链表）的公开行为。

File location: archives/l/libhl/ae3e64484b/test_package/conanfile.py
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibhlTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libhl')}", env="conanrun")
