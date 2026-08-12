#!/usr/bin/env python3
"""test_package for boost-python 1.90.0 — 真实消费者测试。

- CMake find_package(boost_python CONFIG REQUIRED) 找到正式生成的 target
  boost_python::python312（别名 Boost::python312）；
- 编译一个真实 Boost.Python 扩展模块（导出 C++ add/greet）；
- Python 3.12 import 并断言 add(2,3)==5、add(-1,1)==0、greet() 字符串返回值；
- 同时 requires boost/1.90.0.3（传递依赖），验证两包共装无冲突。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class BoostPythonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明基础依赖（任务四.4：验证 boost/1.90.0.3 与 boost-python/1.90.0
        # 同时 requires 时无 BoostConfig/组件/target/include 冲突）
        self.requires("boost/1.90.0.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        # 运行时需能找到 libboost_python312.so（conanrun 环境）、libc++_shared.so（OHOS SDK）
        sdk_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        )
        if os.path.isdir(sdk_lib):
            os.environ["LD_LIBRARY_PATH"] = (
                sdk_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
            )
        script = os.path.join(self.source_folder, "consumer_test.py")
        self.run("python3 " + script, cwd=self.build_folder, env="conanrun")
