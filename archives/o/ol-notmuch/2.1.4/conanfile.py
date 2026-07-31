#!/usr/bin/env python3
"""Conan recipe for ol-notmuch 2.1.4.

Upstream is an Emacs Lisp package. There is no native build step; this recipe
packages the Lisp source and documentation under share/ol-notmuch.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class OlNotmuchConan(ConanFile):
    name = "ol-notmuch"
    version = "2.1.4"
    description = "Org mode links to Notmuch buffers"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/tarsius/ol-notmuch"
    url = ""

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        share = os.path.join(self.package_folder, "share", "ol-notmuch")
        copy(self, "ol-notmuch.el", self.source_folder, os.path.join(share, "lisp"))
        copy(self, "Makefile", self.source_folder, share)
        copy(self, "README.org", self.source_folder, share)
        copy(self, "LICENSE", self.source_folder, share)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        root = os.path.join(self.package_folder, "share", "ol-notmuch")
        self.runenv_info.define("OL_NOTMUCH_ROOT", root)
