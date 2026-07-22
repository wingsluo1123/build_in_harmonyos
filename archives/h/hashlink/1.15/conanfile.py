#!/usr/bin/env python3
"""Conan recipe for hashlink 1.15 on OpenHarmony PC (aarch64, bionic libc).

Adapted for OHOS aarch64. Path A scope:
- Only the core `libhl` shared library is built (PCRE2 + std + GC, all vendored).
- All optional `.hdll` plugin modules (uv/sdl/ssl/sqlite/ui/openal/fmt/heaps/video)
  are disabled — they would require external dependencies (libuv, SDL2, mbedtls,
  sqlite3, etc.) that are not present in the OHOS hnp.
- WITH_VM=OFF: the optional `hl` VM executable is not packaged.
- libhl stays as a shared library (CMakeLists.txt hard-codes SHARED) so the
  .hdll plugin ecosystem can dlopen() it downstream.
- R26 does NOT apply: libhl.so is not a system library name conflict.

License: hashlink is MIT (permissive, no copyleft).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.layout import basic_layout


class HashlinkConan(ConanFile):
    name = "hashlink"
    version = "1.15"
    description = (
        "Hashlink is a virtual machine for Haxe — bytecode interpreter with "
        "built-in GC, PCRE2, and FFI to C libraries. Used to run Haxe-compiled "
        "applications and games on the desktop and embedded targets."
    )
    license = "MIT"
    homepage = "https://hashlink.haxe.org/"
    url = "https://github.com/HaxeFoundation/hashlink"
    topics = ("haxe", "vm", "bytecode", "interpreter", "gc", "pcre2")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,   # libhl is fundamentally SHARED in upstream CMake
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Path A: no Conan recipe dependencies. PCRE2 is vendored in
        # include/pcre/; stdlib, GC, and all bundled helpers compile in-tree.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def configure(self):
        # R37 / libc++ ABI sensitivity: hashlink's headers and templates
        # don't depend on libc++ types, but we drop the setting so two
        # builds with different libcxx versions produce the same package_id.
        pass

    def package_id(self):
        # R33-equivalent for libcxx: bionic's libc++ ABI is unstable across
        # toolchain bumps; drop the setting so consumers don't get spurious
        # rebuild requirements.
        del self.info.settings.compiler.libcxx

    def generate(self):
        tc = CMakeToolchain(self)
        # hashlink's top-level CMakeLists.txt hard-codes BUILD_SHARED_LIBS
        # behavior for libhl (always SHARED) and for the .hdll plugins.
        # We pass BUILD_SHARED_LIBS=OFF defensively; libhl remains SHARED
        # via add_library(... SHARED), but this prevents the .hdll plugins
        # (when WITH_* is re-enabled later) from being STATIC by accident.
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Local cmake 4.x dropped compatibility with cmake_minimum_required
        # < 3.5; hashlink 1.15 declares VERSION 3.1. Pass the policy floor
        # explicitly so configure succeeds.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Path A: kill all optional subsystems.
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["WITH_VM"] = "OFF"
        tc.variables["WITH_FMT"] = "OFF"
        tc.variables["WITH_OPENAL"] = "OFF"
        tc.variables["WITH_SDL"] = "OFF"
        tc.variables["WITH_SQLITE"] = "OFF"
        tc.variables["WITH_SSL"] = "OFF"
        tc.variables["WITH_UI"] = "OFF"
        tc.variables["WITH_UV"] = "OFF"
        tc.variables["WITH_VIDEO"] = "OFF"
        tc.variables["WITH_HEAPS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # hashlink's top-level CMakeLists.txt declares
        # cmake_minimum_required(VERSION 3.1); cmake 4.x dropped support for
        # that and aborts before the toolchain file can set
        # CMAKE_POLICY_VERSION_MINIMUM via CACHE. Pass the policy floor on the
        # command line so the variable is set before cmake_minimum_required()
        # is evaluated.
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy LICENSE so downstream consumers see the MIT notice.
        for license_file in ("LICENSE", "LICENSE.txt", "COPYING"):
            src = os.path.join(self.source_folder, license_file)
            if os.path.exists(src):
                from conan.tools.files import copy
                copy(self, license_file, src, self.package_folder)

    def package_info(self):
        # The actual library is named `hl` (OUTPUT_NAME in CMakeLists.txt
        # line 164), not `hashlink`. The SONAME is libhl.so.1.
        self.cpp_info.libs = ["hl"]
        # R26 doesn't apply (libhl.so is not a system name), but the
        # transitive libs m/dl/pthread are listed as system_libs per the
        # CMakeLists.txt target_link_libraries(libhl m dl pthread) at
        # line 199. They're OHOS-provided, not packaged.
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # Tell pkg-config / CMake find_package consumers the canonical name.
        self.cpp_info.set_property("pkg_config_name", "hashlink")