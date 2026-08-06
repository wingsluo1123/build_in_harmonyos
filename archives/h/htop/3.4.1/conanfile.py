#!/usr/bin/env python3
"""Conan recipe for htop 3.4.1 — Interactive process viewer.

htop is a command-line application (not a library).
Build system: Autotools (configure + make).

Depends on ncurses/6.4 from conancenter. If ncurses is not yet published
to the ohpcd制品仓, the CI build will fail with a dependency error.
Once ncurses is published to ohpcd, this recipe will work correctly.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class HtopConan(ConanFile):
    name = "htop"
    version = "3.4.1"
    description = "Interactive process viewer for Unix systems"
    license = "GPL-2.0"
    homepage = "https://htop.dev/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: Allow both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"htop only supports Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        # ncurses from conancenter (needs to be published to ohpcd制品仓 for CI to pass)
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Set CC/CXX via Conan environment (HarmonyOS has clang but no cc symlink)
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.vars(self).save_script("conanautotools_cc")

        tc = AutotoolsToolchain(self)
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
        self.cpp_info.bindirs = ["bin"]
