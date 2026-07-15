#!/usr/bin/env python3
"""Conan test_package for cdecl 18.7.2 CLI tool."""
import os
import shutil

from conan import ConanFile


class CdeclTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies["cdecl"].package_folder
        cdecl_bin = os.path.join(pkg_folder, "bin", "cdecl")
        script = os.path.join(self.source_folder, "test_cdecl.sh")
        self.run(f'{bash} {script} "{cdecl_bin}"', env="conanrun")
