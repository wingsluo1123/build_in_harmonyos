#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libdaemon, libdaemon, 0.14, Lightweight C library for writing UNIX daemons, LGPL-2.1, https://0pointer.de/lennart/projects/libdaemon/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdaemonConan(ConanFile):
    name = "libdaemon"
    version = "0.14"
    description = "Lightweight C library for writing UNIX daemons"
    license = "LGPL-2.1"
    homepage = "https://0pointer.de/lennart/projects/libdaemon/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 库文件名为 libdaemon.a，CMakeDeps find_library 会自动加 lib 前缀，
        # 因此 libs 必须写去前缀的 "daemon"，否则在 HarmonyOS（CMake 未知平台）上
        # find_library(NAMES libdaemon) 会错误地查找 liblibdaemon.a 而失败。
        self.cpp_info.libs = ["daemon"]
