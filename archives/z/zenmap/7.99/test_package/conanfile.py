#!/usr/bin/env python3
"""Conan consumer test for the installed zenmap package.

Runs the assertions in ``test_core.py`` against the *installed* package: the
``conanrun`` environment provides ``PYTHONPATH`` (from zenmap's
``package_info()``) and the ``nmap/7.99`` run dependency, and the resolved nmap
binary is handed to the tests so they can verify it is the OHOS aarch64 build.
"""
import os
import shutil

from conan import ConanFile


class ZenmapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _nmap_binary(self):
        """Absolute path of the nmap binary from the run dependency."""
        if "nmap" in self.dependencies:
            folder = self.dependencies["nmap"].package_folder
            if folder:
                candidate = os.path.join(folder, "bin", "nmap")
                if os.path.isfile(candidate):
                    return candidate
        return shutil.which("nmap") or ""

    def _shell(self):
        for candidate in (os.environ.get("CONFIG_SHELL"), shutil.which("bash"),
                          "/data/service/hnp/bin/bash", "/bin/sh",
                          "/system/bin/sh"):
            if candidate and os.path.isfile(candidate):
                return candidate
        raise RuntimeError("no POSIX shell found to run the zenmap test_package")

    def test(self):
        self.run(
            'ZENMAP_TEST_NMAP="{}" "{}" test.sh'.format(self._nmap_binary(),
                                                        self._shell()),
            env="conanrun")
