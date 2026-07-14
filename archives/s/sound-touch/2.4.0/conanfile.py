#!/usr/bin/env python3
"""Conan recipe — SoundTouch 2.4.0 (Autotools project).

SoundTouch is an open-source audio processing library for changing
the tempo, pitch, and playback rate of audio streams independently.

Source: https://www.surina.net/soundtouch/
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SoundTouchConan(ConanFile):
    name = "sound-touch"
    version = "2.4.0"
    description = "Open-source audio processing library for tempo, pitch, and rate adjustment"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.surina.net/soundtouch/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.configure_args.append("--disable-neon-optimizations")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # SoundTouch source tarball doesn't include configure script
        # OHOS: bootstrap not executable via shebang, use CONFIG_SHELL
        shell = os.environ.get("CONFIG_SHELL") or "bash"
        src = self.source_folder
        self.run(f"cd {src} && {shell} ./bootstrap")
        # Fix HMDFS umask 077 issue (ref: E100)
        self.run(f"cd {src} && sed -i 's/umask 077/umask 022/g' configure")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["SoundTouch"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "SoundTouch")
        self.cpp_info.set_property("cmake_target_name", "SoundTouch::SoundTouch")
        self.cpp_info.set_property("pkg_config_name", "soundtouch")
