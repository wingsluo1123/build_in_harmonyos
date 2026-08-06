#!/usr/bin/env python3
"""Conan test_package for cleo 0.004 — Perl CLI consumer test.

编译并运行 test_cleo 验证 cleo Perl CLI 安装：
  1. bin/cleo 脚本存在且可执行
  2. perl -c bin/cleo 语法检查通过（间接验证 Perl 模块依赖链可加载）
通过 self.run() 实跑测试程序，满足 R34 + L0 stub_test_method 门禁。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CleoTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # aireview P2: 补 cleo 5 个 Perl 模块依赖到测试包，避 perl -c 找不到 App::Cleo 及依赖模块
        for dep in ("perl-Term-ReadKey", "perl-Term-ANSIColor",
                    "perl-File-Slurp", "perl-Time-HiRes",
                    "perl-ExtUtils-MakeMaker"):
            self.requires(f"{dep}/@latest")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cleo_bin = os.path.join(self.dependencies["cleo"].package_folder,
                                "bin", "cleo")
        perl = os.environ.get("PERL", "perl")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_cleo")
        self.run(f'"{test_bin}" "{cleo_bin}" "{perl}"', env="conanrun")
