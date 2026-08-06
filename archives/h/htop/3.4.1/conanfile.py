#!/usr/bin/env python3
"""Conan recipe for htop 3.4.1 — Interactive process viewer.

htop is a command-line application (not a library).
Build system: Autotools (configure + make).

ncurses is installed from cmd-pkgs pre-compiled package (not conancenter)
because conancenter's ncurses recipe cannot build on HarmonyOS
(config.guess doesn't recognize OHOS, sockaddr_storage redefinition).
"""
import os
import shutil

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
        # Pass ncurses paths to configure
        home = os.path.expanduser("~")
        tc.configure_args.append(f"NCURSES_CFLAGS=-I{home}/usr/local/include")
        tc.configure_args.append(f"NCURSES_LIBS=-L{home}/usr/local/lib -lncursesw")
        tc.configure_args.append(f"LDFLAGS=-L{home}/usr/local/lib")
        tc.generate()

    def build(self):
        # Install ncurses from cmd-pkgs if not already installed
        home = os.path.expanduser("~")
        ncurses_h = os.path.join(home, "usr/local/include/curses.h")
        if not os.path.exists(ncurses_h):
            self.run(
                "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | "
                "sh -s -- ncurses 6.4",
                env="conanbuild"
            )

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
