#!/usr/bin/env python3
"""Conan recipe for lua-resty-dns — pure Lua DNS resolver library.

This is a pure Lua library (no C/C++ compilation). The "build" is simply
copying .lua files to the package directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LuaRestyDnsConan(ConanFile):
    name = "lua-resty-dns"
    version = "0.23"
    description = "Lua DNS resolver for the nginx lua module based on the cosocket API"
    license = "BSD-2-Clause"
    homepage = "https://github.com/openresty/lua-resty-dns"
    url = ""

    package_type = "library"
    settings = "os", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Copy Lua modules from source lib/ to package lib/
        copy(self, "*.lua",
             src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
