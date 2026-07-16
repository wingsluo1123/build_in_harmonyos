#!/usr/bin/env python3
"""Conan recipe — dar 2.7.15 (Disk ARchive, autotools).
Pre-generated configure + config.guess/sub. --host + --build for OHOS."""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

class DarConan(ConanFile):
    name = "dar"
    version = "2.7.15"
    description = "DAR — Disk ARchive, backup and restore tool with compression and encryption"
    license = "GPL-3.0-or-later"
    homepage = "http://dar.linux.free.fr/"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"dar supports Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        os.umask(0)
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
