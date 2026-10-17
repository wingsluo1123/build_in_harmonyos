#!/usr/bin/env python3
"""test_package — miredo 1.2.6 消费者测试（conan create 自动执行）。

验证两件事，均以真实业务语义为准：
1. 消费者用例：仅凭已安装的公开头文件与 miredo::miredo 链接目标，编译、链接并
   运行一个真实第三方使用者 —— 调用 libteredo 公开 API（teredo_create /
   teredo_set_privdata / teredo_get_privdata / teredo_destroy）完成一次隧道对象的
   生命周期，并强制解析 libtun6 符号。
2. CLI 可执行：miredo --version 输出版本号、miredo-checkconf --help 输出用法
   （调用者视角验证，不依赖 TUN 设备与特权）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MiredoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: 跳过运行时验证")
            return

        consumer = os.path.join(self.cpp.build.bindirs[0], "test_miredo_consumer")
        self.run('"%s"' % consumer, env="conanrun")
        self.output.info("✓ 消费者用例通过（libteredo 公开 API 编译/链接/运行）")

        dep = self.dependencies[self.tested_reference_str]
        cpp = dep.cpp_info
        found = {}
        for d in cpp.bindirs:
            for exe in ("miredo", "miredo-checkconf"):
                p = os.path.join(dep.package_folder, d, exe)
                if os.path.isfile(p):
                    found[exe] = p
        for exe in ("miredo", "miredo-checkconf"):
            if exe not in found:
                raise ConanException(
                    "未找到期望的命令行工具 %s（package_folder=%s, bindirs=%s）"
                    % (exe, dep.package_folder, list(cpp.bindirs)))

        # CLI 可执行：调用者视角验证。Conan 2 的 self.run() 只返回退出码，故用
        # subprocess 捕获输出做内容断言；运行库路径按被测包 libdirs 显式构造。
        import subprocess

        env = dict(os.environ)
        libdirs = [os.path.join(dep.package_folder, d)
                   for d in (list(cpp.libdirs) or ["lib"])]
        old_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [p for p in libdirs if p] + ([old_ld] if old_ld else []))

        r = subprocess.run([found["miredo"], "--version"],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0 or "1.2.6" not in (r.stdout + r.stderr):
            raise ConanException("miredo --version 未输出版本号 1.2.6 (rc=%d): %s%s"
                                 % (r.returncode, r.stdout, r.stderr))
        self.output.info("✓ miredo --version 输出 1.2.6")

        r = subprocess.run([found["miredo-checkconf"], "--help"],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0 or "Usage" not in (r.stdout + r.stderr):
            raise ConanException("miredo-checkconf --help 未输出用法 (rc=%d): %s%s"
                                 % (r.returncode, r.stdout, r.stderr))
        self.output.info("✓ miredo-checkconf --help 正常执行")
