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
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoostPythonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明基础依赖（任务四.4：验证 boost/1.90.0.3 与 boost-python/1.90.0
        # 同时 requires 时无 BoostConfig/组件/target/include 冲突）
        self.requires("boost/1.90.0.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeToolchain 只在 generate() 中实例化（不在 generators 声明，避免重复）。
        # OHOS SDK 默认 ld.lld 依赖 libxml2.so.16（CI 沙箱缺失导致链接失败）；
        # 仿照 poppler 模式对三类链接统一追加 ld.bfd：
        #   - CMAKE_EXE_LINKER_FLAGS：CMake try_compile 探测可执行文件链接必需（否则
        #     探测仍调损坏的 lld 而失败）；
        #   - CMAKE_SHARED_LINKER_FLAGS / CMAKE_MODULE_LINKER_FLAGS：test_ext.so 链接。
        # 追加而非覆盖，保留已有 flags。
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            linker = self._find_ld_bfd()
            fuse = "-fuse-ld={}".format(linker)
            for flag in (
                "CMAKE_EXE_LINKER_FLAGS",
                "CMAKE_SHARED_LINKER_FLAGS",
                "CMAKE_MODULE_LINKER_FLAGS",
            ):
                old = tc.variables.get(flag, "")
                tc.variables[flag] = (str(old) + " " + fuse).strip()
        tc.generate()

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

    def _find_ld_bfd(self):
        """结构化解析 OHOS ld.bfd：compiler 目录 → PATH → 标准 HNP 工具目录。

        与主配方一致；找不到时抛 ConanInvalidConfiguration，不静默回退到
        已知损坏的默认 lld（依赖 libxml2.so.16，CI 沙箱缺失）。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, "ld.bfd") if compiler_dir else "",
            shutil.which("ld.bfd") or "",
            os.path.join("/data/service/hnp/bin", "ld.bfd"),
            "/data/service/hnp/binutils.org/binutils_2.45/bin/ld.bfd",
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        raise ConanInvalidConfiguration(
            "OHOS consumer link requires ld.bfd (default SDK ld.lld depends on "
            "libxml2.so.16 which is unavailable in the CI sandbox)."
        )

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
