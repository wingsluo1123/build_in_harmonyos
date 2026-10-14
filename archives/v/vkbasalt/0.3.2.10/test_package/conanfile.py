#!/usr/bin/env python3
"""test_package for vkbasalt 0.3.2.10.

vkBasalt 是 Vulkan implicit layer（运行时由 Vulkan loader 加载，不直接链接
libvulkan）。测试策略：
  1. dlopen 加载 libvkbasalt.so，验证 layer 可被动态加载（鸿蒙 ELF 签名/
     依赖完整性在加载期暴露的问题会在此处失败）；
  2. dlsym 检查 layer 导出的关键符号（vkGetInstanceProcAddr / vkCreateInstance），
     证明 layer 的 dispatch 入口完整；
  3. 校验层配置文件 vkBasalt.json 已随包安装（implicit layer 注册依赖它）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sysroot_lib_dir(self):
        # libc++_shared.so 位于 OHOS sysroot（运行测试程序需要它，但 conanrun
        # 只注入 requires 库目录）。本机与 CI worker 的 sysroot 布局不同，
        # 用 glob 探测常见位置。
        candidates = [
            "/storage/Users/currentUser/usr/local/sysroot/usr/lib/aarch64-linux-ohos",
            "/storage/Users/currentUser/ohos-sdk/sysroot/usr/lib/aarch64-linux-ohos",
        ]
        candidates += sorted(glob.glob(
            "/data/service/hnp/*/ohos/native/sysroot/usr/lib/aarch64-linux-ohos"))
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "libc++_shared.so")):
                return candidate
        return None

    def test(self):
        if cross_building(self):
            return
        # 显式注入被测包 lib 目录 + sysroot lib（libc++_shared.so）+ 包根
        # （TEST_PACKAGE_ROOT 供测试程序定位 vkBasalt.json），确保运行时
        # 能找到 libvkbasalt.so、系统 C++ 运行时与层配置文件。
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(
            self.dependencies["vkbasalt"].package_folder, "lib"))
        sysroot_lib = self._sysroot_lib_dir()
        if sysroot_lib:
            env.prepend_path("LD_LIBRARY_PATH", sysroot_lib)
        env.define("TEST_PACKAGE_ROOT",
                   self.dependencies["vkbasalt"].package_folder)
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindir, "test_vkbasalt"),
                     env="conanrun")
