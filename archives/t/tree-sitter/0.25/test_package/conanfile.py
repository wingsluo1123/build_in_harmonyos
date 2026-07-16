#!/usr/bin/env python3
"""Compile and run a minimal Tree-sitter C API consumer."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TreeSitterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["tree-sitter"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "test_tree_sitter.c")
        executable = os.path.join(self.build_folder, "test_tree_sitter")
        self.run(
            '"{}" -I"{}" "{}" -L"{}" -ltree-sitter -o "{}"'.format(
                cc,
                os.path.join(dependency.package_folder, "include"),
                source,
                os.path.join(dependency.package_folder, "lib"),
                executable,
            )
        )
        if can_run(self):
            self.run('"{}"'.format(executable), env="conanrun")
