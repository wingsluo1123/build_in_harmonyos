#!/usr/bin/env python3
"""Conan recipe — dfu-util 0.11 (USB DFU firmware upgrade tool)

Build system: autotools (configure + make)
License: GPL-2.0-or-later
Homepage: http://dfu-util.sourceforge.net/
Source:   https://github.com/Stefan-Schmidt/dfu-util

Products: dfu-util, dfu-suffix, dfu-prefix executables
Dependency: libusb
"""

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DfuUtilConan(ConanFile):
    name = "dfu-util"
    version = "0.11"
    description = "USB DFU (Device Firmware Upgrade) host utilities"
    license = "GPL-2.0-or-later"
    homepage = "http://dfu-util.sourceforge.net/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Terminal tool: no linkable library, only executables
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
