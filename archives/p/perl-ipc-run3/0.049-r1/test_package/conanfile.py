#!/usr/bin/env python3
"""Conan test_package — perl-ipc-run3 0.049-r1

Tests that IPC::Run3 can be loaded and used to run subprocesses
with I/O redirection on OpenHarmony.

Test script: test_ipc_run3.sh — exercises load, stdout capture,
stdin pipe, stderr capture, and exit code handling.
"""
import os
import glob

from conan import ConanFile


class PerlIpcRun3TestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find IPC/Run3.pm in the package to verify artifact exists
        pkg = self.dependencies["perl-ipc-run3"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Run3.pm"), recursive=True)
        if not pm_files:
            raise Exception("IPC/Run3.pm not found in package")
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
        self.output.info(f"Found IPC/Run3.pm at {pm_files[0]}")

        # Set PERL5LIB so test script can find the module
        self.runenv_info.append_path("PERL5LIB", lib_dir)

        # Run the comprehensive test script
        test_script = os.path.join(self.source_folder, "test_ipc_run3.sh")
        self.run(f'bash "{test_script}"', env="conanrun")
