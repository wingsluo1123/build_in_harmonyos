#!/usr/bin/env python3
"""Conan test_package — kea 3.2.0 (consumer view).

Four checks run against the packaged server suite:

* ``test_kea_api``       - compiles against the packaged include/kea headers
  (including boost-dependent ones), links the packaged libkea-exceptions and
  libkea-util libraries and drives their public API;
* ``test_ohos_platform`` - HarmonyOS-specific: the packaged kea-dhcp4 daemon
  carries the OHOS aarch64 / musl / libc++ platform ABI signature and the OHOS
  loader maps it;
* ``test_ohos_runtime``  - HarmonyOS-specific: every packaged Kea library and
  hook plug-in resolves its NEEDED closure under the OHOS loader, and the hook
  contract (version()/load()/unload()) is importable;
* ``test_kea_daemons.py``- real execution of the packaged daemons: -v version
  output, the -W config report (the build-time generated config_report.cc
  path) and the -t configuration check on valid and invalid configurations.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaTestConan(ConanFile):
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
            self.output.info("cross-building: kea consumer tests skipped")
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bindir = self.cpp.build.bindirs[0]
        dhcp4 = os.path.join(pkg, "bin", "kea-dhcp4")
        libdir = os.path.join(pkg, "lib")
        self.run('"{}/test_kea_api"'.format(bindir), env="conanrun")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, dhcp4),
                 env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, libdir),
                 env="conanrun")
        script = os.path.join(self.source_folder, "test_kea_daemons.py")
        self.run('"{}" "{}" "{}"'.format(sys.executable, script, pkg),
                 env="conanrun")
