import os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, cmake_layout


class LuaTermTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Build lua from source with LUA_USE_DLOPEN support.
        # The conancenter lua package doesn't enable dlopen on OHOS because
        # CMake doesn't set UNIX for the HarmonyOS platform.
        get(self, "https://www.lua.org/ftp/lua-5.4.7.tar.gz",
            sha256="9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30",
            destination=self.build_folder, strip_root=False)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        lua_dir = os.path.join(self.build_folder, "lua-5.4.7", "src")
        self.run(f"make -C {os.path.dirname(lua_dir)} linux CC={cc} -j1")

        cmake = CMake(self)
        cmake.configure(cli_args=[f"-DLUA_DIR={lua_dir}"])
        cmake.build()

    def test(self):
        lua_term = self.dependencies["lua-term"]
        pkg = lua_term.package_folder

        os.environ["LUA_CPATH"] = os.path.join(pkg, "lib", "lua", "5.4", "?.so")
        os.environ["LUA_PATH"] = ";".join([
            os.path.join(pkg, "res", "lua", "5.4", "?.lua"),
            os.path.join(pkg, "res", "lua", "5.4", "?", "init.lua"),
            "",
        ])

        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_lua_term")
        self.run(test_exe)
