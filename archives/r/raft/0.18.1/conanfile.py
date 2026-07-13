#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Raft, raft, 0.18.1, Raft consensus algorithm library, Apache-2.0, https://github.com/canonical/raft
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RaftConan(ConanFile):
    name = "raft"
    version = "0.18.1"
    description = "Raft consensus algorithm library"
    license = "Apache-2.0"
    homepage = "https://github.com/canonical/raft"
    url = "https://github.com/canonical/raft"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libuv/1.52.1")
        self.requires("lz4/1.10.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # raft is a library (not a terminal tool), use dynamic linking
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
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
        self.cpp_info.libs = ["raft"]
