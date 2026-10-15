#!/usr/bin/env python3
"""test_package — 消费者端到端用例（rule12 鸿蒙特有测试）。

真实调用 ezc3d 的完整流程：构造 C3D → 写盘 → 读回 → 逐点比对数值。
不是纯断言/纯头文件检查，而是库的 write/read 回环全链路。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class Ezc3dTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeDeps 必须显式声明：它才会在 generators/ 下生成 ezc3d-config.cmake
        # 等消费者侧查找文件，供 CMakeLists.txt 里的 find_package(ezc3d CONFIG) 使用。
        # 只生成 CMakeToolchain 时 CMAKE_PREFIX_PATH 指向 generators/ 却没有配置文件，
        # 于是 configure 阶段报 "Could not find a package configuration file
        # provided by \"ezc3d\""。
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emulator(self):
        """返回可用的 aarch64 模拟器前缀；没有则 None（永不抛异常）。"""
        import os
        emu = self.conf.get("tools.cmake.cmaketoolchain:extra_variables", default={},
                            check_type=dict).get("CMAKE_CROSSCOMPILING_EMULATOR")
        if emu:
            return emu
        runroot = os.environ.get("OHOS_RUNROOT", "/root/ohpc/sdk/ohos-runroot")
        qemu = os.environ.get("OHOS_QEMU", "/root/ohpc/sdk/qemu/usr/bin/qemu-aarch64-static")
        if os.path.isfile(qemu):
            return "%s -L %s" % (qemu, runroot)
        return None

    def test(self):
        exe = "ezc3d_consumer_test"
        # ★顺序关键★ 必须**先**按 settings.os 判断目标平台，再看 can_run()。
        # os=OHOS 时产物是 aarch64/OHOS，无论 can_run() 返回什么都不可能直接在
        # x86_64 宿主上执行 —— 实测 can_run() 在 OHOS profile 下会误报 True，
        # 旧代码据此 `RUN: ezc3d_consumer_test` → /bin/dash: not found, exit 127。
        if self.settings.os == "OHOS":
            emulator = self._emulator()
            if emulator:
                # 交叉构建：经 qemu + 真机 musl 运行根执行
                self.run("%s ./%s" % (emulator, exe))
                return
            # 交叉编译且无模拟器（如 CI worker）：用例已编译+链接成功（即构建证据），
            # 但本机跑不了。环境能力缺失不是配方缺陷，如实跳过而不是硬失败。
            self.output.warning(
                "== test_package 消费者用例已编译+链接成功，但目标为 OHOS/aarch64 且未提供"
                "模拟器（OHOS_QEMU / CMAKE_CROSSCOMPILING_EMULATOR 均不可用）—— 跳过执行。")
            return

        if can_run(self):
            self.run(exe, env="conanrun")
            return
        self.output.warning(
            "== test_package 消费者用例已编译+链接成功，但本机无法执行该目标产物 —— 跳过执行。")
