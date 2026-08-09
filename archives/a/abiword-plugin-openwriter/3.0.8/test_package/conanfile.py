#!/usr/bin/env python3
"""Conan test_package for abiword-plugin-openwriter 3.0.8 — Conan L1 official test.

R34 API surface test: verifies that libgsf satisfies all 11 libgsf
symbols openwriter actually calls (see test_openwriter.c).

Cross-compiled binary (OHOS/ARM64) is smoke-tested via qemu-aarch64
outside this CI gate (per libgsf R-NEW 2026-08-10 / Phase 2.3).
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class AbiwordPluginOpenwriterTestConan(ConanFile):
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
            self.output.info(
                f"cross-building: only verify compile+link (L2 via qemu-aarch64) "
                f"[settings.arch={host_arch}, machine={native_machine}]"
            )
            return
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            bash = (shutil.which("bash") or shutil.which("sh") or "/bin/sh")
        self.run(f"{bash} -c './test_openwriter'", env="conanrun")
