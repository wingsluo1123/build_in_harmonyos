#!/usr/bin/env python3
"""Conan test_package for kywc 1.3.2 — installed-consumer E2E.

Builds a C consumer against the installed package through pkg-config
(`kywc` + `wayland-client`), starts an in-process Wayland server and runs the
public libkywc API cases in test_kywc.c.  On OHOS the same binary is also
re-run from a private inode by harmony_tests/private_signed_loader.py, which
checks the real .codesign section and the actual loader path.
"""
import os
import shlex
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KywcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps", "CMakeDeps", \
                 "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The PkgConfigDeps wayland-client.pc aggregates every wayland
        # component (client/server/cursor/egl) plus expat/libxml2/libffi; the
        # cursor/egl ELFs are rejected by the OHOS loader and must not leak
        # into the link.  Write a minimal wayland-client.pc and hand its
        # directory to CMake, which puts it first on PKG_CONFIG_PATH before
        # pkg_check_modules runs (same fix as the library recipe).
        wayland_base = self.dependencies["wayland"].package_folder
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        with open(os.path.join(fixed_pc_dir, "wayland-client.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={wayland_base}\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n\n"
                    "Name: Wayland Client\n"
                    "Description: Wayland client library\n"
                    "Version: 1.24.0\n"
                    "Libs: -L${libdir} -lwayland-client\n"
                    "Cflags: -I${includedir}\n")
        tc = CMakeToolchain(self)
        tc.cache_variables["WAYLAND_CLIENT_PC_DIR"] = fixed_pc_dir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_kywc")
        self.run(f'"{executable}"', env="conanrun")
        if str(self.settings.os) == "OHOS":
            scenario = (Path(self.source_folder)
                        / "harmony_tests/private_signed_loader.py")
            self.run(shlex.join([sys.executable, str(scenario), executable]),
                     env="conanrun", cwd=self.build_folder)
