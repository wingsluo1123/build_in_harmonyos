#!/usr/bin/env python3
"""Conan recipe — tmux 3.4 (Autotools, terminal application).

tmux is a terminal multiplexer. Statically linked for OHOS portability.

R26: Terminal tools must be statically linked (--enable-static --disable-shared).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TmuxConan(ConanFile):
    name = "tmux"
    version = "3.4"
    description = "tmux is a terminal multiplexer — multiple terminals in a single window"
    license = "ISC"
    homepage = "https://github.com/tmux/tmux"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")
        self.requires("libevent/2.1.12")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
        ])

        libevent = self.dependencies["libevent"]
        event_libdir = ":".join(libevent.cpp_info.libdirs)
        event_incdir = ":".join(libevent.cpp_info.includedirs)

        tc.configure_args.append(
            f"EVENT_CFLAGS=-I{event_incdir}"
        )
        tc.configure_args.append(
            f"EVENT_LIBS=-L{event_libdir} -levent_core -levent_extra"
        )

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # L1: Run upstream official test suite (make check)
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
