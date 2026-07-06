#!/usr/bin/env python3
"""Conan recipe — bluez-alsa v4.3.1 (Autotools)."""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


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
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-payloadcheck")
        tc.generate()
        # E001: Set CC/CXX for autotools on OHOS
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.vars(self, scope="build").save_script("conanbuild_env")

    def build(self):
        apply_conandata_patches(self)
        # Generate configure script if not present (GitHub tarball lacks it)
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            self.run("autoreconf -fi", cwd=self.source_folder)
            configure_path = os.path.join(self.source_folder, "configure")
        # E165: Fix shebangs for OpenHarmony
        for f in glob.glob(os.path.join(self.source_folder, "**", "*.sh"), recursive=True):
            try:
                replace_in_file(self, f, "#!/bin/bash", "#!/data/service/hnp/bin/bash")
            except Exception:
                pass
            try:
                replace_in_file(self, f, "#!/bin/sh", "#!/system/bin/sh")
            except Exception:
                pass
        if os.path.exists(configure_path):
            try:
                replace_in_file(self, configure_path, "#!/bin/sh", "#!/system/bin/sh")
            except Exception:
                pass
            try:
                replace_in_file(self, configure_path, "#!/bin/bash", "#!/data/service/hnp/bin/bash")
            except Exception:
                pass
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["bluez-alsa"]
