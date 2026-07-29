#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "Terminal handling and screen optimization library"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ncurses supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--without-debug",
                "--without-ada",
                "--without-cxx",
                "--without-cxx-binding",
                "--without-manpages",
                "--without-progs",
                "--without-tests",
                "--without-shared",
                "--with-normal",
                "--enable-widec",
                "--enable-overwrite",
                "--enable-pc-files",
                "--disable-db-install",
                "--disable-symlinks",
            ]
        )
        if self.options.fPIC:
            tc.extra_cflags.append("-fPIC")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["formw", "menuw", "panelw", "ncursesw"]
        self.cpp_info.set_property("cmake_file_name", "ncurses")
        self.cpp_info.set_property("cmake_target_name", "ncurses::ncurses")
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
