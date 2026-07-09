#!/usr/bin/env python3
"""Conan recipe for nettle 3.10.2 — Autotools project.

Nettle is a low-level cryptographic library.
"""

import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NettleConan(ConanFile):
    name = "nettle"
    version = "3.10.2"
    description = "Low-level cryptographic library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.lysator.liu.se/~nisse/nettle/"
    url = "https://git.lysator.liu.se/nettle/nettle"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Set CONFIG_SHELL to use correct bash for HarmonyOS
        import shutil
        bash_path = shutil.which("bash") or "/bin/bash"
        # Use environment variables for configure
        env = tc.environment()
        env.define("CONFIG_SHELL", bash_path)
        env.define("SHELL", bash_path)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Set environment variables for configure
        import os
        bash_path = shutil.which("bash") or "/bin/bash"
        env_vars = {
            "CONFIG_SHELL": bash_path,
            "SHELL": bash_path
        }
        # Update environment for subprocess
        for key, value in env_vars.items():
            os.environ[key] = value
        
        autotools = Autotools(self)
        autotools.configure(args=["--disable-shared", "--enable-static"])
        autotools.make(args=[f"SHELL={bash_path}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["nettle", "hogweed"]
        self.cpp_info.includedirs = ["include"]