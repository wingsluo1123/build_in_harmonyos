#!/usr/bin/env python3
"""Conan recipe for lua-struct 0.9.2 — pure Lua binary pack/unpack library."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaStructConan(ConanFile):
    name = "lua-struct"
    version = "0.9.2"
    description = "Implementation of binary packing/unpacking in pure Lua"
    license = "MIT"
    homepage = "https://github.com/iryont/lua-struct"
    url = ""

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Lua library — no compilation step needed

    def package(self):
        copy(self, "struct.lua",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "lib", "lua", "5.4"))

    def package_info(self):
        self.cpp_info.libdirs = ["lib/lua/5.4"]
        self.cpp_info.libs = []
        # Expose LUA_PATH so consumers can find the struct module
        lua_path = os.path.join(self.package_folder, "lib", "lua", "5.4", "?.lua")
        self.runenv_info.append("LUA_PATH", f"{lua_path};;")
