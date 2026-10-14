#!/usr/bin/env python3
"""Conan test_package for manifold 3.5.2 — HarmonyOS consumer validation.

两个层面:

Layer 1 — 真实 API 消费测试 (test_manifold.cpp):
  用打包后的头文件和库链一个最小几何程序, 覆盖核心 API 面:
  Manifold 构造/布尔 (Boolean OpType Add/Subtract/Intersect),
  CrossSection (2D, 消费 clipper2 后端), manifoldc (C 绑定),
  属性/体积/表面积计算。在真机 (HarmonyOS PC aarch64) 上执行。

Layer 2 — OHOS 专项 ABI 检查 (ohos_abi_check.py):
  对产物 ELF 做静态解析 (纯 Python, 无外部工具):
  ELF64/AArch64、musl loader、DT_NEEDED、SONAME、无 glibc 符号版本、
  无宿主绝对 RPATH 等真实 OHOS 目标属性验证。
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ManifoldTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        # tested_reference_str 是 conan create 内建的注入点
        self.requires(self.tested_reference_str)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"manifold test supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if (
            self.dependencies["manifold"].options.shared
        ) else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 始终运行 Layer 1: 在设备上执行真实 API 消费程序
        if not can_run(self):
            self.output.info(
                "cross-building: runtime API test skipped on this host")
            return

        bin_dir = os.path.join(self.build_folder, "bin")
        self.run(os.path.join(bin_dir, "test_manifold"), env="conanrun")

        # Layer 2: OHOS ELF 专项检查
        if str(self.settings.os) == "OHOS":
            dep = self.dependencies.get("manifold")
            if dep is None:
                raise ConanException("manifold dependency missing from graph")
            libdir = None
            try:
                libdir = dep.cpp_info.libdirs[0]
            except Exception:
                libdir = os.path.join(dep.package_folder, "lib")
            self.run(" ".join(shlex.quote(a) for a in (
                sys.executable,
                os.path.join(self.recipe_folder, "ohos_abi_check.py"),
                "--libdir", libdir)))
        else:
            self.output.info(
                "target os=%s: OHOS ABI layer is skipped" % self.settings.os)
