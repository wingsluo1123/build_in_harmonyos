#!/usr/bin/env python3
"""Conan recipe for ragel 6.10 — State Machine Compiler (Autotools).

Ragel is a command-line tool that compiles state machines from regular
language descriptions into C/C++/D/Java/Ruby/Go code. It is a build tool
(application), not a library.

Platform adaptation for OHOS:
  1. configure umask fix: HMDFS requires umask 0002 instead of 077
     for temporary directory creation during autoconf.

R32: settings.os check uses "in" for OHOS compatibility.
R28: test_package/ exists with real functional tests.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RagelConan(ConanFile):
    name = "ragel"
    version = "6.10"
    description = "State machine compiler that generates C/C++/D/Java/Ruby code from regular expressions"
    license = "GPL-2.0"
    homepage = "https://www.colm.net/open-source/ragel/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
