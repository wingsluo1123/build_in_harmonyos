#!/usr/bin/env python3
"""test_package for boost-python 1.90.0 — 真实消费者测试。

- CMake find_package(boost_python CONFIG REQUIRED) 找到正式生成的 target
  boost_python::python312（别名 Boost::python312）；
- 编译一个真实 Boost.Python 扩展模块（导出 C++ add/greet）；
- OHOS dlopen 要求 ELF code signature：import 前对 CMake 生成的 test_ext.so 签名；
- Python 3.12 import 并断言 add(2,3)==5、add(-1,1)==0、greet() 字符串返回值；
- 同时 requires boost/1.90.0.3（传递依赖），验证两包共装无冲突。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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
        # OHOS dlopen 要求 ELF code signature：import 前签名 CMake 实际生成的扩展模块
        if str(self.settings.os) == "OHOS":
            extension = self._find_extension()
            if extension:
                self._sign_elf_atomically(
                    extension,
                    self._find_ohos_tool("llvm-objcopy"),
                    self._find_ohos_tool("binary-sign-tool"),
                )
        script = os.path.join(self.source_folder, "consumer_test.py")
        self.run("python3 " + script, cwd=self.build_folder, env="conanrun")

    def _find_extension(self):
        matches = [
            os.path.join(self.build_folder, "test_ext.so"),
            os.path.join(self.build_folder, "test_ext.cpython-312-aarch64-linux-ohos.so"),
        ]
        for path in matches:
            if os.path.isfile(path):
                return path
        return ""

    def _sign_elf_atomically(self, path, objcopy, signer):
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer import requires llvm-objcopy and binary-sign-tool "
                "to sign the extension module (dlopen enforces ELF code signature)."
            )
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
