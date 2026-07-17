#!/usr/bin/env python3
"""Conan recipe — gtkspell3 3.0.10-r3 (GTK spell checker, autotools).
Pre-generated configure. --host + --build for OHOS."""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

class Gtkspell3Conan(ConanFile):
    name = "gtkspell3"
    version = "3.0.10-r3"
    description = "GtkSpell3 — spell-checking for GTK+ text widgets"
    license = "LGPL-2.1-or-later"
    homepage = "https://gtkspell.sourceforge.net/"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"gtkspell3 supports Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        if self.options.shared:
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
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
        self.cpp_info.libs = ["gtkspell3-3"]
