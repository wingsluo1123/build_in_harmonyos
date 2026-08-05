#!/usr/bin/env python3
"""Test package for vusted."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import copy


class VustedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    lua_path_deps = (
        "vusted",
        "busted",
        "lua_cliargs",
        "luasystem",
        "dkjson",
        "lua-say",
        "luassert",
        "lua-term",
        "lua-penlight",
        "mediator_lua",
    )
    lua_cpath_deps = ("luasystem", "lua-term", "luafilesystem")

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("neovim/0.11.3")
        self.requires("busted/2.2.0-1")
        self.requires("lua_cliargs/3.0.2-1")
        self.requires("luasystem/0.6.3-1")
        self.requires("dkjson/2.8-1")
        self.requires("lua-say/1.4.1-3")
        self.requires("luassert/1.9.0-1")
        self.requires("lua-term/0.7")
        self.requires("lua-penlight/1.15.0")
        self.requires("mediator_lua/1.1.2-0")
        self.requires("luafilesystem/1.8.0-1")

    def build(self):
        copy(self, "smoke_spec.lua", src=self.recipe_folder, dst=self.build_folder)

    def _lua_path(self):
        paths = []
        for dep_name in self.lua_path_deps:
            pkg = self.dependencies[dep_name].package_folder
            lua_share = os.path.join(pkg, "share", "lua", "5.4")
            paths.extend([os.path.join(lua_share, "?.lua"), os.path.join(lua_share, "?", "init.lua")])
        return ";".join(paths) + ";;"

    def _lua_cpath(self):
        paths = []
        for dep_name in self.lua_cpath_deps:
            pkg = self.dependencies[dep_name].package_folder
            lua_lib = os.path.join(pkg, "lib", "lua", "5.4")
            paths.extend([os.path.join(lua_lib, "?.so"), os.path.join(lua_lib, "?", "core.so")])
        return ";".join(paths) + ";;"

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        env.prepend_path("PATH", os.path.join(self.dependencies["vusted"].package_folder, "bin"))
        env.prepend_path("PATH", os.path.join(self.dependencies["neovim"].package_folder, "bin"))
        env.define("LUA_PATH", self._lua_path())
        env.define("LUA_CPATH", self._lua_cpath())
        env.define("VUSTED_ARGS", "--headless --clean -u NONE -i NONE")
        with env.vars(self).apply():
            self.run(f'vusted "{os.path.join(self.build_folder, "smoke_spec.lua")}"')
