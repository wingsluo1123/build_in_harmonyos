#!/usr/bin/env python3
"""Conan test_package for libgsf 1.14.58 — Conan L1 official test.

Uses CMakeDeps + CMakeToolchain (R33 compliant). CMakeLists.txt finds
libgsf-1 via find_package(libgsf-1 REQUIRED CONFIG). CI runs this
automatically via ``conan create``.

The downstream consumer is cross-compiled (OHOS/ARM64); native execution
is skipped via cross_building() check (R32).
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class GsfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        host_arch = str(self.settings.get_safe("arch", ""))
        native_machine = platform.machine().lower()
        conan_to_machine = {"armv8": "aarch64", "x86_64": "x86_64", "amd64": "x86_64"}
        machine_arch = conan_to_machine.get(host_arch, host_arch)
        is_native_executable = (machine_arch == native_machine)
        if cross_building(self) or not is_native_executable:
            # L2 smoke test on cross-compiled binary is performed via
            # qemu-aarch64 outside this CI gate (see notes.md).
            self.output.info(
                f"cross-building: only verify compile+link (L2 via qemu-aarch64) "
                f"[settings.arch={host_arch}, machine={native_machine}]"
            )
            return
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            bash = (shutil.which("bash") or shutil.which("sh") or "/bin/sh")
        self.run(f"{bash} -c './test_gsf'", env="conanrun")
