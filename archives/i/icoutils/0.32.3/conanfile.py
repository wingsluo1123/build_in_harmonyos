#!/usr/bin/env python3
"""Conan recipe for icoutils — Extract and convert Windows icon/cursor resources.

Autotools build (configure + make). Produces command-line tools: icotool, wrestool,
extresso, genresscript.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class IcoutilsConan(ConanFile):
    name = "icoutils"
    version = "0.32.3"
    description = "Extract and convert Windows icon and cursor resources (ICO/CUR/ANI)"
    license = "GPL-3.0"
    homepage = "https://www.nongnu.org/icoutil/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
