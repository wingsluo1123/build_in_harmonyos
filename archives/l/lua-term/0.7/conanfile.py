#!/usr/bin/env python3
"""Conan recipe — lua-term 0.7 (makefile)

A terminal manipulation library for Lua.
Depends on lua/5.4.7 for headers.
Produces core.so Lua C extension module.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuaTermConan(ConanFile):
    name = "lua-term"
    version = "0.7"
    description = "A terminal manipulation library for Lua"
    license = "MIT"
    homepage = "https://github.com/hoelzro/lua-term"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

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

        # Get compiler from Conan conf (R33: never use shell env vars)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Get Lua include directory from the dependency package
        lua_inc = os.path.join(self.dependencies["lua"].package_folder, "include")

        # lua-term uses a simple Makefile; LUA_INC must point to Lua headers
        self.run(f"make -C {self.source_folder} CC={cc} LUA_VER=5.4 LUA_INC={lua_inc} -j1")

    def package(self):
        # Install the C extension module
        copy(self, "core.so", self.source_folder,
             os.path.join(self.package_folder, "lib", "lua", "5.4", "term"))
        # Install the Lua module files
        copy(self, "*.lua", os.path.join(self.source_folder, "term"),
             os.path.join(self.package_folder, "res", "lua", "5.4", "term"))
        # License
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["core"]
        self.cpp_info.libdirs = ["lib/lua/5.4/term"]
        self.cpp_info.resdirs = ["res/lua/5.4/term"]
        # Declare transitive dependency on lua (consumers need lua headers/lib)
        self.cpp_info.requires = ["lua::lua"]
