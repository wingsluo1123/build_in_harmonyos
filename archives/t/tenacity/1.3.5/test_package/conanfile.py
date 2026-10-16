#!/usr/bin/env python3
"""Conan test_package — tenacity 1.3.5（路径 B：非 GUI 核心库）

验证内容（R34 非空壳，非仅归档检查）：
  A. 归档完整性：licenses/ 非空；lib/ 含全部 17 个 lib-*.a；include/tenacity/<lib>/
     17 个目录均非空（与 recipe 的 cpp_info.libs / includedirs 一一对应）。
  B. 真实编译链接：find_package(tenacity REQUIRED) + target_link_libraries(
     test_tenacity PRIVATE tenacity::tenacity)，编译 test_tenacity.cpp。
  C. 真实执行（鸿蒙消费者用例）：在 aarch64 主机上直接运行 --selftest，
     调用 lib-math 的 SamplesToFloats/ClearSamples/ReverseSamples 与
     lib-string-utils 的 Tenacity::ToUTF8/ToWString 并断言结果；同时 fail-closed
     断言运行环境无 DISPLAY / WAYLAND_DISPLAY（wxBase-only 消费者不得依赖显示服务）。
  D. 产物验证：elf_check 逐一确认 17 个 .a 为合法 ar 归档且成员为 AArch64 ELF。

说明：OHOS 交叉编译产物在本机（aarch64 OHOS）可直接执行，实测无需显式签名，
故这里不因 cross_building 跳过运行；仅当真机架构不是 aarch64 时降级为提示。
"""
import glob
import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

# 与 conanfile.py 的 cpp_info.libs 保持一致的 17 个核心库
LIBRARIES = [
    "lib-project-rate", "lib-screen-geometry", "lib-project",
    "lib-audio-devices", "lib-xml", "lib-utility", "lib-track",
    "lib-strings", "lib-registries", "lib-string-utils",
    "lib-preferences", "lib-math", "lib-files", "lib-ffmpeg-support",
    "lib-exceptions", "lib-components", "lib-basic-ui",
]


class TenacityTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    # VirtualRunEnv：canonical CMake test_package 模板要求——self.run(..., env="conanrun")
    # 需要 generators 目录下的 conanrun.sh；仅 CMakeDeps+CMakeToolchain 不会生成它。
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # L0c 门禁：test_package 必须有测试源文件（test_tenacity.cpp 真实编译）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _check_archive(self, pkg):
        licenses = os.path.join(pkg, "licenses")
        if not os.path.isdir(licenses) or not os.listdir(licenses):
            raise ConanException(f"tenacity archive missing licenses/: {licenses}")

        for lib in LIBRARIES:
            archive = os.path.join(pkg, "lib", f"{lib}.a")
            if not os.path.isfile(archive):
                raise ConanException(f"tenacity archive missing static lib: {archive}")

        for lib in LIBRARIES:
            inc = os.path.join(pkg, "include", "tenacity", lib)
            if not os.path.isdir(inc) or not os.listdir(inc):
                raise ConanException(
                    f"tenacity archive missing headers for {lib}: {inc}")
        self.output.info(
            f"archive verified: licenses + {len(LIBRARIES)} static libs + "
            f"{len(LIBRARIES)} header dirs")

    def test(self):
        pkg = self.dependencies["tenacity"].package_folder
        self._check_archive(pkg)

        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_package build folder (bindirs) is empty")
        # 关键：cpp.build.bindirs 是**相对**路径（实测 cmake_layout 下为 '.'，
        # os.path.isabs() == False）。self.run() 默认 cwd=self.build_folder 故
        # 相对路径可用，但 os.path.isfile() 相对的是 conan 进程的 cwd，会误判为
        # "未构建"。此处显式拼接 build_folder。
        build_dir = bindirs[0]
        if not os.path.isabs(build_dir):
            build_dir = os.path.join(self.build_folder, build_dir)
        test_bin = os.path.join(build_dir, "test_tenacity")
        elf_check = os.path.join(build_dir, "elf_check")
        for exe in (test_bin, elf_check):
            if not os.path.isfile(exe):
                raise ConanException(f"test_package binary not built: {exe}")

        if platform.machine() != "aarch64":
            self.output.warning(
                f"host arch is {platform.machine()}, OHOS aarch64 binaries cannot "
                "be executed here; compile+link verified only")
            return

        # C. 真实执行消费者用例（含 lib-math / lib-string-utils 双库断言）
        self.run(f'"{test_bin}" --selftest', env="conanrun")

        # D. 产物验证：全部 17 个归档均为含 AArch64 ELF 成员的合法 ar 归档
        archives = sorted(glob.glob(os.path.join(pkg, "lib", "*.a")))
        if len(archives) != len(LIBRARIES):
            raise ConanException(
                f"expected {len(LIBRARIES)} archives, found {len(archives)}: {archives}")
        args = " ".join(f'"{a}"' for a in archives)
        self.run(f'"{elf_check}" {args}', env="conanrun")

        self.output.info(
            "tenacity test_package PASSED (consumer selftest ran headless + "
            f"{len(archives)} AArch64 ar archives verified)")
