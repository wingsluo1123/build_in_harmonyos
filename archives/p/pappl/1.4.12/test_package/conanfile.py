#!/usr/bin/env python3
"""Conan consumer test for PAPPL 1.4.12."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PapplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # pappl 的公共头（base.h）包含 <cups/cups.h>/<cups/ipp.h>，需显式
        # 声明传递依赖，让 CMakeDeps 生成 cups 的 target（libppd 同款做法）。
        self.requires("cups/2.4.19")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "test_pappl")
            tmpdir = os.path.join(self.build_folder, "pappl-tmp")
            os.makedirs(tmpdir, exist_ok=True)
            self.run('TMPDIR=%s TEMP=%s %s' % (tmpdir, tmpdir, executable),
                     env="conanrun")

            dependency = self.dependencies[self.tested_reference_str]
            package = dependency.package_folder
            script = os.path.join(self.source_folder, "test_pappl_ohos.sh")
            os.chmod(script, 0o644)
            self.run('/system/bin/sh %s %s' % (script, package),
                     env="conanrun")
