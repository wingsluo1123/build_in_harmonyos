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

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _ohos_triplet(arch):
        gnu_arch = {
            "armv7": "arm",
            "armv7hf": "arm",
            "armv8": "aarch64",
            "armv8_3": "aarch64",
            "armv8.3": "aarch64",
            "arm64": "aarch64",
            "aarch64": "aarch64",
            "x86": "i686",
            "x86_64": "x86_64",
        }.get(str(arch))
        if gnu_arch is None:
            raise ConanInvalidConfiguration(f"unsupported OHOS architecture: {arch}")
        return f"{gnu_arch}-unknown-linux-ohos"

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            triplet = self._ohos_triplet(self.settings.arch)
            tc.configure_args.extend(
                [
                    f"--build={triplet}",
                    f"--host={triplet}",
                ]
            )
        tc.configure_args.extend(
            [
                f"--srcdir={self.source_folder}",
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
