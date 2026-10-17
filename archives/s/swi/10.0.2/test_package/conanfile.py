#!/usr/bin/env python3
"""Build C embedding/foreign-module consumers and run Prolog integration tests."""

import os
import shlex
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class SwiTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, headers=True, libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        package = self.dependencies["swi"].package_folder
        executable = os.path.join(package, "bin", "swipl")
        suite = os.path.join(self.source_folder, "test_swi.pl")
        extension = os.path.join(self.build_folder, "native_sum.so")
        embed = os.path.join(self.build_folder, "embed_swi")
        parent = "/data/storage/el2/base/temp"
        if not os.path.isdir(parent):
            parent = self.build_folder
        with tempfile.TemporaryDirectory(prefix="swi-consumer-", dir=parent) as temporary:
            environment = Environment()
            environment.define("TMPDIR", temporary)
            environment.define("TMP", temporary)
            environment.define("TEMP", temporary)
            with environment.vars(self).apply():
                self.run("timeout 120 {} -q -f none --on-error=status -s {} -g 'run_tests,halt' -t 'halt(1)' -- {}".format(
                    shlex.quote(executable), shlex.quote(suite), shlex.quote(extension)), env="conanrun")
                self.run(shlex.quote(embed), env="conanrun")
