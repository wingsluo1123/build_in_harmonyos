#!/usr/bin/env python3
"""Conan test package — CVM 0.97 (CMake)."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class CvmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
            self.output.info("Cross-compiling: consumer binaries were built but cannot run")
            return
        bindir = self.cpp.build.bindirs[0]
        consumer = os.path.join(bindir, "cvm_consumer")
        helper = os.path.join(bindir, "cvm_marker_helper")
        failure = os.path.join(bindir, "cvm_pipe_failure")
        marker = os.path.join(self.build_folder, "unexpected-module-execution")
        self.run(consumer, env="conanrun")
        environment = Environment()
        environment.define("CVM_PIPE_MARKER", marker)
        with environment.vars(self).apply():
            self.run(
                shlex.join([failure, helper, marker]),
                env="conanrun",
            )
        package_bin = os.path.join(
            self.dependencies["cvm"].package_folder,
            "bin",
        )
        package_root = self.dependencies["cvm"].package_folder
        self.run(
            shlex.join([
                "python3",
                os.path.join(self.source_folder, "test_commands.py"),
                package_bin,
                self.build_folder,
            ]),
            env="conanrun",
        )
        self.run(
            shlex.join([
                "python3",
                os.path.join(self.source_folder, "test_elf.py"),
                package_root,
            ]),
            env="conanrun",
        )
