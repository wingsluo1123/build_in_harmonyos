#!/usr/bin/env python3
"""Conan test_package for lua-struct — embeds Lua and tests struct.pack/unpack."""
import os

from conan import ConanFile


class LuaStructTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.4.7")

    def build(self):
        lua_info = self.dependencies["lua"].cpp_info
        inc_dirs = lua_info.includedirs
        lib_dirs = lua_info.libdirs
        libs = lua_info.libs
        sys_libs = lua_info.system_libs

        lua_includes = " ".join(f"-I{d}" for d in inc_dirs)
        lua_libdirs = " ".join(f"-L{d}" for d in lib_dirs)
        lua_libs = " ".join(f"-l{lib}" for lib in libs)
        system_libs = " ".join(f"-l{lib}" for lib in sys_libs)

        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = tools.get("c", "clang")
        src = os.path.join(self.source_folder, "test_lua_struct.c")
        self.run(
            f'{cc} {src} {lua_includes} {lua_libdirs} {lua_libs} {system_libs} '
            f'-o test_lua_struct'
        )

    def test(self):
        self.run(os.path.join(self.build_folder, "test_lua_struct"), env="conanrun")
