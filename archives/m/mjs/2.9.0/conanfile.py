#!/usr/bin/env python3
"""Conan recipe — mjs 2.9.0 (single-file amalgamated C library)."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MjsConan(ConanFile):
    name = "mjs"
    version = "2.9.0"
    description = "Embedded-friendly JavaScript engine for C/C++"
    license = "GPL-2.0-only"
    homepage = "https://github.com/cesanta/mjs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("javascript", "engine", "embedded", "c")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compilers(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c")
        if not cc:
            raise ConanException("tools.build:compiler_executables must define c")
        toolchain_dir = os.path.dirname(cc)
        ar = executables.get("ar", os.path.join(toolchain_dir, "llvm-ar"))
        ranlib = executables.get("ranlib", os.path.join(toolchain_dir, "llvm-ranlib"))
        for tool in (cc, ar, ranlib):
            if not os.path.isfile(tool):
                raise ConanException(f"Conan toolchain executable not found: {tool}")
        return cc, ar, ranlib

    def _build_environment(self, cc):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            compiler = os.path.realpath(cc)
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            if not os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                raise ConanException(
                    f"OHOS SDK linker runtime not found in active toolchain: {llvm_lib}"
                )
            environment.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return environment

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compilers()
        with self._build_environment(cc).vars(self).apply():
            self.run(f'"{cc}" -fPIC -O2 -c "{self.source_folder}/mjs.c" -o mjs.o')
            self.run(f'"{ar}" rcs libmjs.a mjs.o')
            self.run(f'"{ranlib}" libmjs.a')

    def package(self):
        copy(
            self,
            "mjs.h",
            self.source_folder,
            os.path.join(self.package_folder, "include"),
        )
        copy(self, "libmjs.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mjs"]
        self.cpp_info.system_libs = ["m", "dl"]
        self.cpp_info.set_property("cmake_file_name", "mjs")
        self.cpp_info.set_property("cmake_target_name", "mjs::mjs")
        self.cpp_info.set_property("pkg_config_name", "mjs")
