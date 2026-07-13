#!/usr/bin/env python3
"""Conan test_package — automysqlbackup 3.0-rc6

Tests that the automysqlbackup script is installed and functional.
Since this is a shell script package, we test by running the script directly.
"""
import os

from conan import ConanFile


class AutomysqlbackupTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the automysqlbackup script in the dependency's package folder
        dep = self.dependencies["automysqlbackup"]
        bin_dir = None
        if hasattr(dep, 'cpp_info') and dep.cpp_info.bindirs:
            bin_dir = dep.cpp_info.bindirs[0]
        elif hasattr(dep, 'package_folder'):
            bin_dir = os.path.join(dep.package_folder, "bin")

        if bin_dir:
            script_path = os.path.join(bin_dir, "automysqlbackup")
            if os.path.exists(script_path):
                self.run(f"bash {script_path} -h")
                return

        # Fallback: try conanrun env
        self.run("automysqlbackup -h", env="conanrun")
