#!/usr/bin/env python3
"""Conan recipe — spek 0.8.5 (Autotools, headless CLI build)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpekConan(ConanFile):
    name = "spek"
    version = "0.8.5"
    description = "Spek - Acoustic spectrum analyser (headless CLI build)"
    license = "GPL-3.0"
    homepage = "https://www.spek.cc/"
    url = "https://github.com/alexkay/spek"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # Headless build: skip wxWidgets GUI
        tc.configure_args.append("--disable-gui")
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # Use system-installed FFmpeg libraries (pre-built packages, not conan packages)
        if self.settings.os in ("Linux", "OHOS"):
            self.buildenv_info.append_path("PKG_CONFIG_PATH", "/storage/Users/currentUser/usr/local/lib/pkgconfig")

    def build(self):
        apply_conandata_patches(self)
        # Regenerate configure from patched configure.ac (patch adds --disable-gui)
        # Use autoconf instead of autoreconf -fi (autopoint not available on CI worker)
        self.run("autoconf", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]