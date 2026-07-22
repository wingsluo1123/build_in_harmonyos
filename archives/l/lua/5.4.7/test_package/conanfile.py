import os

from conan import ConanFile


class LuaTestConan(ConanFile):
    """test_package for Lua 5.4.7 — both library AND executable consumer.

    R34 compliance:
    - Binary smoke test: `lua -v` must print "Lua 5.4".
    - Library API test: <lua.h> pulls in lua_State + lua_pushinteger +
      lua_close; test_lua.c calls them on a fresh state and asserts the
      stack side-effect (Lua 5.4 stores small integers in the integer
      field, no allocation). Avoids triggering bionic stub functions
      (inet_ntop / strtoul) — Lua's API surface is pure user-space.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Pass the installed package folder directly so test.sh can locate
        # lua/luac binaries and liblua.a via absolute paths. This avoids
        # the VirtualRunEnv PATH-injection path, which on conan 2.29.1
        # sometimes emits empty conanrunenv-*.sh for library-typed packages.
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        env_vars = f"LUA_PACKAGE_FOLDER={pkg_folder}"
        self.run(f"{env_vars} {bash} test.sh", env="conanrun")