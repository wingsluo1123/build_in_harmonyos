#!/usr/bin/env python3
"""Conan recipe for RPM Package Manager 6.0.2 - CMake based build.

Dependencies (popt, zlib, bzip2, sqlite3, xz, zstd, readline, openssl,
libarchive, lua) are installed as system packages via cmd-pkgs.
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class RpmConan(ConanFile):
    name = "rpm"
    version = "6.0.2"
    description = "The RPM Package Manager"
    license = "GPL-2.0-or-later"
    homepage = "https://rpm.org"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        sys_prefix = os.environ.get("HNP_PREFIX")
        if not sys_prefix:
            raise ConanInvalidConfiguration("HNP_PREFIX environment variable is not set. Please set it to the system prefix path (e.g. /usr/local).")
        pkg_config_path = sys_prefix + "/lib/pkgconfig"
        if os.path.exists(pkg_config_path):
            old = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = pkg_config_path + (":" + old if old else "")

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.cache_variables["CMAKE_PREFIX_PATH"] = sys_prefix
        tc.variables["ENABLE_PYTHON"] = False
        tc.variables["ENABLE_PLUGINS"] = True
        tc.variables["ENABLE_TESTSUITE"] = False
        tc.variables["ENABLE_NLS"] = False
        tc.variables["ENABLE_OPENMP"] = False
        tc.variables["WITH_CAP"] = False
        tc.variables["WITH_ACL"] = False
        tc.variables["WITH_SELINUX"] = False
        tc.variables["WITH_DBUS"] = False
        tc.variables["WITH_AUDIT"] = False
        tc.variables["WITH_FAPOLICYD"] = False
        tc.variables["WITH_SEQUOIA"] = False
        tc.variables["WITH_OPENSSL"] = True
        tc.variables["WITH_READLINE"] = True
        tc.variables["WITH_BZIP2"] = True
        tc.variables["WITH_ICONV"] = False
        tc.variables["WITH_ZSTD"] = True
        tc.variables["WITH_LIBDW"] = False
        tc.variables["WITH_LIBELF"] = False
        tc.variables["WITH_LIBLZMA"] = True
        tc.cache_variables["CMAKE_SKIP_BUILD_RPATH"] = "OFF"
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        # Explicitly set Lua paths since FindLua has trouble with custom layouts
        lua_lib = sys_prefix + "/lib/liblua.so"
        lua_inc = sys_prefix + "/include"
        if os.path.exists(lua_lib):
            tc.variables["LUA_LIBRARY"] = lua_lib
        if os.path.exists(lua_inc + "/lua.h"):
            tc.variables["LUA_INCLUDE_DIR"] = lua_inc
        # HarmonyOS has no separate libm (math is in libc)
        tc.variables["LUA_MATH_LIBRARY"] = ""
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["rpm", "rpmio", "rpmbuild", "rpmsign"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
