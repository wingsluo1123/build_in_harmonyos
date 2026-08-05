#!/usr/bin/env python3
"""Conan recipe for busted 2.2.0-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BustedConan(ConanFile):
    name = "busted"
    version = "2.2.0-1"
    description = "Elegant Lua unit testing framework"
    license = "MIT"
    homepage = "https://lunarmodules.github.io/busted/"
    url = "https://github.com/lunarmodules/busted"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("lua_cliargs/3.0.2-1")
        self.requires("luasystem/0.6.3-1")
        self.requires("dkjson/2.8-1")
        self.requires("lua-say/1.4.1-3")
        self.requires("luassert/1.9.0-1")
        self.requires("lua-term/0.7")
        self.requires("lua-penlight/1.15.0")
        self.requires("mediator_lua/1.1.2-0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "busted.lua", src=self.source_folder, dst=lua_share)
        copy(self, "*.lua", src=os.path.join(self.source_folder, "busted"), dst=os.path.join(lua_share, "busted"))
        copy(self, "busted", src=os.path.join(self.source_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        command = os.path.join(self.package_folder, "bin", "busted")
        if os.path.exists(command):
            os.chmod(command, 0o755)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;",
        )

