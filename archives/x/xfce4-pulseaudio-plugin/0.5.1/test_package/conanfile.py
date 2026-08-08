#!/usr/bin/env python3
"""Conan test_package — verifies xfce4-pulseaudio-plugin .so is valid.

R34: Test uses dlopen to verify the plugin .so exists, is a valid ELF,
and exports the xfce_panel_module_init entry-point symbol.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Xfce4PulseaudiopluginTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["xfce4-pulseaudio-plugin"]
        so_path = os.path.join(
            dep.package_folder,
            "lib", "xfce4", "panel", "plugins",
            "libpulseaudio-plugin.so"
        )
        self.run(f"{os.path.join(self.cpp.build.bindir, 'test_xfce4-pulseaudio-plugin')} {so_path}", env="conanrun")
