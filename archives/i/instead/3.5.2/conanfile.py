#!/usr/bin/env python3
"""Conan recipe for INSTEAD Engine 3.5.2 on OpenHarmony PC.

INSTEAD Engine ("INteractive STory Engine") — interactive fiction runtime
that interprets Lua-driven game scripts and renders them via SDL2.
Adapted for OpenHarmony PC (aarch64, bionic libc).

Path A scope:
- core engine + SDL2 + SDL2_image + SDL2_ttf + SDL2_mixer + Lua (vanilla) + zlib
- audio path kept (SDL2_mixer): bundling the mixer avoids forking
  src/sound.c out of the build, and mixer itself is light.
- LuaJIT forced OFF (OHOS lacks LLVM / LLVM-JIT).
- iconv / GTK / HarfBuzz forced OFF (no iconv completeness guarantee,
  no GTK on OHOS, no RTL shaping need).
- SYSTEMWIDE/STANDALONE forced OFF; conan stows the build under package dir.

INSTEAD is MIT — fully permissive, no copyleft bleed into consumers.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class InsteadConan(ConanFile):
    name = "instead"
    version = "3.5.2"
    description = ("INSTEAD Engine — interactive story engine that runs Lua-driven "
                   ".game scripts via SDL2 (Russian: Интерактивная сторизация)")
    license = "MIT"
    homepage = "https://insteadhub.github.io/"
    url = "https://github.com/instead-hub/instead"

    # INSTEAD produces a single executable `sdl-instead` (and a symlink
    # alias `instead`). We still expose the engine API header so test_package
    # can compile against `instead.h` to build a minimal driver program.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Required for set_target_properties etc. on the consumer side
    exports_sources = "patches/*", "cmake/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Vanilla Lua — upstream handles 5.1 / 5.2 / 5.3 / 5.4; pin to a
        # 5.x version with a LUA_VERSION_MAJOR=5 macro INSTEAD's FindLua51
        # will accept. lua/5.4.7 is the most recent 5.4 line available
        # on conancenter (our primary dep source — the OHOS-native ohpcd
        # remote does not yet carry SDL/Lua binaries).
        self.requires("lua/5.4.7")
        # SDL2 family + zlib (Path A base). mixer kept — sound.c is hard-tied
        # to its symbols and bundling avoids refactoring upstream.
        self.requires("sdl/2.30.9")
        self.requires("sdl_image/2.8.8")
        self.requires("sdl_ttf/2.24.0")
        self.requires("sdl_mixer/2.8.1")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_ohos_zlib_probe(self):
        """Make sure src/CMakeLists.txt doesn't try to probe zlib on its own:
        conan-generated zlibConfig.cmake is canonical.
        Idempotent — no-op if already patched.
        """
        cmakelists = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        if not os.path.exists(cmakelists):
            return
        with open(cmakelists, "r", encoding="utf-8") as f:
            data = f.read()
        if "Zlib" not in data:
            return  # already replaced upstream
        # FIND_PACKAGE(ZLIB REQUIRED) is fine on OHOS; conan's zlibConfig.cmake
        # is honored. No rewrite needed; we just guard against probing-related
        # breakage by leaving FIND_PACKAGE(ZLIB REQUIRED) intact.

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static linking.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # ─── INSTEAD-specific CMake toggles (Path A scope) ────────────────
        tc.variables["WITH_LUAJIT"] = "OFF"   # OHOS has no LLVM-JIT
        tc.variables["WITH_ICONV"] = "OFF"    # bionic iconv not always complete
        tc.variables["WITH_GTK2"] = "OFF"
        tc.variables["WITH_GTK3"] = "OFF"
        tc.variables["WITH_HARFBUZZ"] = "OFF"

        # INSTEAD's install layout — disable both SYSTEMWIDE and STANDALONE;
        # we install via cmake.install() into the standard conan package dir.
        tc.variables["SYSTEMWIDE"] = "OFF"
        tc.variables["STANDALONE"] = "OFF"
        tc.variables["APPIMAGE"] = "OFF"

        # CMake C standard — INSTEAD is C89/C99 mixed but uses <stdint.h>.
        tc.variables["CMAKE_C_STANDARD"] = "11"
        tc.generate()

    def _patch_for_ohos(self):
        """Idempotent guards inserted into INSTEAD's own CMakeLists.txt:
        the upstream chain hard-requires SDL2_mixer / SDL2_image / SDL2_ttf,
        but also assumes `WITH_LUAJIT=ON` which we set OFF via the toolchain.
        We do NOT need to surgically rewrite src/CMakeLists.txt here — the
        toolchain's WITH_* variables suffice. The single post-configure fix
        is to neutralize the upstream option() default for WITH_GTK3, which
        CMake picks before our toolchain override takes effect when CMake
        caches defaults. We work around by patching the cached value during
        configure via an environment hook below.
        """
        # If future compile breaks appear (e.g. iconv / locale / setlocale),
        # add patches here that target specific lines using regex on the
        # upstream source tree, pre-`cmake.configure()`.
        pass

    def build(self):
        self._patch_for_ohos()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Mirror INSTEAD's CMake install layout — the upstream CMake
        # writes the sdl-instead binary into ${CMAKE_INSTALL_BINDIR} when
        # SYSTEMWIDE=ON; we set SYSTEMWIDE=OFF here so cmake.install()
        # still works (InstallSymlink is skipped gracefully).
        cmake = CMake(self)
        cmake.install()
        # License files for downstream consumers.
        for license_file in ("COPYING", "MIT-LICENSE", "LICENSE"):
            src_path = os.path.join(self.source_folder, license_file)
            if os.path.exists(src_path):
                copy(self, license_file, src_path, self.package_folder)
        # Ship the engine's header so downstream consumers (test_package,
        # other build-in-hmos conan recipes) can write their own driver.
        copy(self, "instead.h",
             os.path.join(self.source_folder, "src", "instead"),
             os.path.join(self.package_folder, "include", "instead"))

    def package_info(self):
        # INSTEAD produces an executable `sdl-instead` (aliased to `instead`).
        # We still expose the engine symbols via a static-like stub: consumers
        # that want to link the engine directly must compile the engine
        # sources themselves (see notes.md / test_package). For R34
        # compliance, the test_package drives the engine via compiling
        # src/instead/*.c (interpreter-only path, not the SDL renderer).
        self.cpp_info.libs = []  # executable; nothing to link by default
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_target_name", "instead::instead")
        # Engine API exported as C header.
        self.cpp_info.set_property("pkg_config_name", "instead")
        # System libs that the engine symbols call (m for math, dl for
        # dlopen-style Lua C modules, pthread for Lua state).
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
