#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Bluezalsa, bluez-alsa, v4.3.1, Bluetooth ALSA audio bridge for BlueZ stack, MIT, https://github.com/arkq/bluez-alsa
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BluezalsaConan(ConanFile):
    name = "bluez-alsa"
    version = "v4.3.1"
    description = "Bluetooth ALSA audio bridge for BlueZ stack"
    license = "MIT"
    homepage = "https://github.com/arkq/bluez-alsa"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("alsa-lib/1.2.12@ohpcd/stable")
        self.requires("bluez/5.79@ohpcd/stable")
        self.requires("dbus/1.15.8@ohpcd/stable")
        self.requires("glib/2.84.0@ohpcd/stable")
        self.requires("sbc/1.5@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
        tc.configure_args.append("--prefix=/storage/Users/currentUser/usr/local")
        tc.configure_args.append("--enable-payloadcheck")
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
        self.cpp_info.libs = ["bluez-alsa"]
