#!/usr/bin/env python3
"""Conan recipe — gphoto2 2.5.32 (command-line tool).

gphoto2 is the command-line interface to libgphoto2, providing
camera access, file transfer, and configuration capabilities.

This is a CLI tool (package_type=application), not a library.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class Gphoto2Conan(ConanFile):
    name = "gphoto2"
    version = "2.5.32"
    description = "The gphoto2 command-line tool for digital camera access"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/gphoto/gphoto2"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libgphoto2/2.5.31")
        self.requires("libexif/0.6.26")
        self.requires("popt/1.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix configure's umask and temp dir path for OHOS compatibility
        # (configure uses umask 077 and ./confXXXXXX which causes issues on OHOS)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path,
                        'umask 077 && mktemp -d "./confXXXXXX"',
                        'umask 022 && mktemp -d "${HOME}/tmp/confXXXXXX"')
        replace_in_file(self, configure_path,
                        'tmp=./conf$$-$RANDOM',
                        'tmp=${HOME}/tmp/conf$$-$RANDOM')
        replace_in_file(self, configure_path,
                        '(umask 077 && mkdir "$tmp")',
                        '(umask 022 && mkdir "$tmp")')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
