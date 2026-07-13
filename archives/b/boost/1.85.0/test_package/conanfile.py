#!/usr/bin/env python3
"""Conan test package for the Boost.Build b2 command-line tool."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class BoostTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        for filename in ("Jamroot", "hello.c"):
            source = os.path.join(self.source_folder, filename)
            target = os.path.join(self.build_folder, filename)
            if os.path.abspath(source) != os.path.abspath(target):
                shutil.copy(source, target)

    def test(self):
        b2 = os.path.join(self.dependencies["boost"].package_folder, "bin", "b2")
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c")
        cxx = executables.get("cpp")
        if not cc or not cxx or not os.path.isabs(cc) or not os.path.isabs(cxx):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables.c/cpp must be absolute paths"
            )
        user_config = os.path.join(self.build_folder, "user-config.jam")
        with open(user_config, "w", encoding="utf-8") as stream:
            stream.write(f'using clang : ohos : "{cxx}" : <compileflags>"--target=aarch64-linux-ohos" ;\n')
        self.run(f'"{b2}" --help', cwd=self.build_folder)
        command = (
            f'CC="{cc}" CXX="{cxx}" "{b2}" '
            f'--user-config="{user_config}" toolset=clang-ohos -j1'
        )
        self.run(command, cwd=self.build_folder)
        candidates = []
        expected_dir = os.path.join(self.build_folder, "bin", "clang-linux-ohos")
        for root, _, files in os.walk(expected_dir):
            if "hello" in files:
                candidates.append(os.path.join(root, "hello"))
        assert candidates, "b2 did not build the hello executable"
        self.run(f'"{candidates[0]}"', cwd=self.build_folder)
