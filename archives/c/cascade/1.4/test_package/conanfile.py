#!/usr/bin/env python3
"""Conan test_package for cascade 1.4 — runs the installed CLI on consumer-made RF cascades."""
import os
import shutil

from conan import ConanFile


class CascadeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_cascade.sh")
        cascade = os.path.join(pkg_folder, "bin", "cascade")
        shell = shutil.which("sh") or "/bin/sh"
        self.run(f'"{shell}" "{script}" "{cascade}" "{pkg_folder}" "{self.build_folder}"',
                 env="conanrun")
