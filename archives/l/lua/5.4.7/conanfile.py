#!/usr/bin/env python3
"""Conan recipe for Lua 5.4.7 on OpenHarmony PC.

Lua is a system same-name library; per R26 we ship static-only to avoid
polluting /lib. The build is the upstream Makefile plus a 'linux' target
(NOT linux-readline — libreadline is not on OHOS).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LuaConan(ConanFile):
    name = "lua"
    version = "5.4.7"
    description = ("Lua is a powerful, efficient, lightweight, embeddable scripting "
                   "language. It supports procedural, object-oriented, functional, "
                   "data-driven programming and data description.")
    license = "MIT"
    homepage = "https://www.lua.org/"
    url = "https://www.lua.org/ftp/lua-5.4.7.tar.gz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Lua is fully standalone — no transitive Conan deps.
        pass

    def layout(self):
        basic_layout(self)
        # Lua builds in-source (Makefile expects src/ as the build dir).
        self.folders.build = "src"
        self.folders.source = "."  # so src/ is at <src>/src/

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # We can't just set env vars for the *build* — upstream Makefile's
        # `CC= gcc -std=gnu99` at line 7 of src/Makefile acts as a Makefile-
        # defined variable that overrides any environment CC. We must pass CC
        # on the command line, which is what the recipe's `make` invocation
        # in build() does.
        # For the *consumption* env (VirtualRunEnv), we explicitly add bin/
        # to PATH so test_package can locate `lua` and `luac`. Without this,
        # conan 2.29.1 sometimes fails to aggregate cpp_info.bindirs for
        # library-typed packages — the consumer's conanrunenv-release-*.sh
        # is emitted empty.
        env = Environment()
        env.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        env.vars(self).save_script("lua_bin_path")

    def build(self):
        apply_conandata_patches(self)
        # Use `-j1` because HMDFS rejects make's jobserver mkfifo creation,
        # which breaks `-j$(nproc)`. Pass toolchain vars on the command
        # line so they win over Makefile's `CC= gcc -std=gnu99` assignment.
        # Drop "-Wl,-E" (exported-symbols flag from upstream linux target)
        # — not needed for static lib and trips lld on OHOS.
        cc = os.environ.get("CC", "clang") + " -std=gnu99"
        ar = os.environ.get("AR", "ar")
        ranlib = os.environ.get("RANLIB", "ranlib")
        make_cmd = (
            f"make -j1 "
            f"CC='{cc}' AR='{ar} rcu' RANLIB='{ranlib}' "
            f"SYSCFLAGS='-DLUA_USE_LINUX' "
            f"SYSLIBS='-ldl' "
            f"SYSLDFLAGS='' "
            f"MYCFLAGS='' MYLDFLAGS='' MYLIBS='' "
            f"linux"
        )
        self.run(make_cmd, cwd=self.build_folder)

    def package(self):
        # Headers — Lua ships them at the top level of the tarball
        # (lua.h, luaconf.h, lauxlib.h, lualib.h, ...). Copy them flat
        # into <pkg>/include so downstream can do `#include <lua.h>`
        # without a src/ subdir. We don't recurse into src/ because that
        # contains private headers (ldo.h, lvm.h, ...) that are not part
        # of the public API surface.
        copy(self, "*.h",
             self.source_folder,
             os.path.join(self.package_folder, "include"),
             keep_path=False)
        # Static archive (per R26, never .so/.dylib).
        copy(self, "liblua.a",
             self.build_folder,
             os.path.join(self.package_folder, "lib"))
        # CLI tools — many downstream test_packages (INSTEAD included)
        # exec `lua --version` to verify the build.
        copy(self, "lua",
             self.build_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "luac",
             self.build_folder,
             os.path.join(self.package_folder, "bin"))
        # License.
        copy(self, "doc/lua.html",
             self.source_folder,
             os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "doc/readme.html",
             self.source_folder,
             os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lua"]
        self.cpp_info.system_libs = ["m", "dl"]
        # Lua ships CLI tools (lua / luac) that downstream consumers (INSTEAD
        # included) exec for sanity checks. Advertise bin/ so VirtualRunEnv
        # adds it to PATH in test_package runs.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "lua")

    def package_id(self):
        # Delete compiler.libcxx: bionic libc++ ABI is consistent
        # across OHOS profiles; no need to vary per toolchain.
        del self.info.settings.compiler.libcxx
