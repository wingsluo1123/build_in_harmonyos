#!/usr/bin/env python3
"""Build wxLua with the published GTK3 wxWidgets and Lua packages."""
import os
import importlib.util
from pathlib import Path
from conan.tools.env import VirtualRunEnv
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

class WxLuaConan(ConanFile):
    name = "wxlua"
    version = "3.2.0.2"
    license = "wxWindows"
    homepage = "https://github.com/pkulchenko/wxlua"
    description = "Lua bindings and applications for wxWidgets with the GTK Broadway backend"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [False], "fPIC": [True]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("wxwidgets-gtk3/3.2.10", transitive_headers=True, transitive_libs=True)
        self.requires("lua/5.4.8", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "gui_runner.py", os.path.join(self.recipe_folder, "test_package"), os.path.join(self.export_sources_folder, "test_package"))

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="wxlua-source.tar.gz", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Generated binding translation units are expensive under -O3 on the device.
        tc.variables["CMAKE_C_FLAGS_RELEASE"] = "-O2 -DNDEBUG"
        tc.variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O2 -DNDEBUG"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.variables["wxLua_WX_CONFIG_PACKAGE"] = "wxwidgets-gtk3"
        tc.variables["wxLua_WX_CONFIG_TARGET"] = "wxwidgets-gtk3::wxwidgets-gtk3"
        tc.variables["wxWidgets_VERSION"] = "3.2.10"
        components = "stc;xrc;richtext;propgrid;html;aui;adv;core;xml;net;base"
        tc.variables["wxWidgets_COMPONENTS"] = components
        tc.variables["wxLuaBind_COMPONENTS"] = components
        tc.variables["wxLua_LUA_LIBRARY_USE_BUILTIN"] = False
        tc.variables["wxLua_LUA_LIBRARY_VERSION"] = "5.4"
        lua = self.dependencies["lua"]
        tc.variables["wxLua_LUA_INCLUDE_DIR"] = os.path.join(lua.package_folder, "include")
        tc.variables["wxLua_LUA_LIBRARY"] = os.path.join(lua.package_folder, "lib", "liblua.a")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="wxLua")
        cmake.build()
        helper = Path(self.source_folder) / "test_package" / "gui_runner.py"
        spec = importlib.util.spec_from_file_location("wxlua_gui_runner", helper)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        runtime = dict(os.environ)
        runtime.update(VirtualRunEnv(self).vars().items())
        binary = Path(self.build_folder) / "bin" / str(self.settings.build_type) / "wxLua"
        suite = Path(self.source_folder) / "wxLua" / "samples" / "unittest.wx.lua"
        code = 'dofile([[' + str(suite) + ']]); assert(tests_run == 98 and failed_tests == 0); print("WXLUA_UPSTREAM_PASS 98"); os.exit(0)'
        runner.run_gui([binary, "-e", code], Path(self.dependencies["gtk"].package_folder) / "bin" / "broadwayd", runtime, Path(self.build_folder) / "upstream-evidence", "WXLUA_UPSTREAM_PASS 98")

    def package(self):
        CMake(self).install()
        # Upstream export embeds the build machine's Lua path; Conan provides relocatable targets.
        for config in (Path(self.package_folder) / "share" / "wxlua").glob("wxLuaConfig*.cmake"):
            config.unlink()
        copy(self, "libwx.so", os.path.join(self.package_folder, "lib"), os.path.join(self.package_folder, "lib", "lua", "5.4"))
        module = Path(self.package_folder) / "lib" / "lua" / "5.4" / "libwx.so"
        if module.exists():
            module.rename(module.with_name("wx.so"))
        copy(self, "licence.txt", os.path.join(self.source_folder, "wxLua", "docs"), os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["wxlua_bind-wx-3.2.0.2", "wxlua_debugger-wx-3.2.0.2", "wxlua_debug-wx-3.2.0.2", "wxlua-wx-3.2.0.2"]
        # The package also ships the wxLua/wxLuaCan/wxLuaFreeze applications.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/wxlua"]
        self.cpp_info.set_property("cmake_file_name", "wxlua")
        self.cpp_info.set_property("cmake_target_name", "wxlua::wxlua")
        self.cpp_info.defines = ["wxLUA_USEBINDING_WXGL=0", "wxLUA_USEBINDING_WXMEDIA=0", "wxLUA_USEBINDING_WXWEBVIEW=0"]
        self.cpp_info.requires = ["wxwidgets-gtk3::wxwidgets-gtk3", "lua::lua"]
        self.runenv_info.prepend("LUA_CPATH", os.path.join(self.package_folder, "lib", "lua", "5.4", "?.so"), separator=";")
