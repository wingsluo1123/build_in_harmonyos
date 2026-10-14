"""Conan recipe for the sacc 1.07 Gopher client."""

import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SaccConan(ConanFile):
    name = "sacc"
    version = "1.07"
    description = "Small terminal Gopher client"
    license = "ISC"
    homepage = "https://git.codemadness.org/sacc/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libressl/3.9.1")
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _make_args(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or "cc"
        tls_root = self.dependencies["libressl"].package_folder
        curses_root = self.dependencies["ncurses"].package_folder
        includes = (
            f"-I{shlex.quote(os.path.join(tls_root, 'include'))} "
            f"-I{shlex.quote(os.path.join(curses_root, 'include'))}"
        )
        library_dirs = (
            f"-L{shlex.quote(os.path.join(tls_root, 'lib'))} "
            f"-L{shlex.quote(os.path.join(curses_root, 'lib'))}"
        )
        values = {
            "CC": compiler,
            "UI": "ti",
            "IO": "tls",
            "SACCCFLAGS": (
                "-Os -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=700 "
                "-D_BSD_SOURCE -D_GNU_SOURCE -DUSE_TLS " + includes
            ),
            "SACCLDFLAGS": library_dirs,
            "IOLIBS": "-ltls -lssl -lcrypto -lpthread",
            "LIBS": "-lncursesw",
        }
        return " ".join(shlex.quote(f"{key}={value}") for key, value in values.items())

    def build(self):
        self.run(
            f"make -C {shlex.quote(self.source_folder)} -j1 {self._make_args()}",
            env="conanbuild",
        )

    def package(self):
        self.run(
            f"make -C {shlex.quote(self.source_folder)} "
            f"{self._make_args()} "
            f"{shlex.quote('DESTDIR=' + self.package_folder)} PREFIX= install",
            env="conanbuild",
        )
        copy(
            self, "LICENSE", self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
