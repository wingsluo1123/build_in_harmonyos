#!/usr/bin/env python3
"""Conan recipe for libtwirc 0.1.2.

libtwirc is a Twitch IRC client library written in C. Upstream uses hand-written
shell scripts (build-shared / build-static) that invoke the compiler directly on
src/libtwirc.c (which #includes the sibling *.c units); there is no configure or
Makefile. R39: the source URL is the official GitHub archive of the v0.1.2 tag.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, mkdir, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

# Compiler binaries are supplied through the profile conf (ci/conan/profiles/ohos-aarch64)
# via tools.build:compiler_executables, so build() never depends on undefined shell
# environment variables (R33). ar/ranlib come from the same toolchain PATH.


class LibtwircConan(ConanFile):
    name = "libtwirc"
    version = "0.1.2"
    description = "A Twitch IRC client library written in C (libircclient-like interface)."
    license = "MIT"
    homepage = "https://github.com/domsson/libtwirc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def layout(self):
        self.folders.build = "build"
        self.folders.source = "."
        self.folders.package = "package"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _cc(self):
        # Prefer compiler from the toolchain conf; fall back to 'clang'.
        binaries = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return binaries.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        src = os.path.join(self.source_folder, "src")
        obj = os.path.join(self.build_folder, "obj")
        mkdir(self, obj)
        # libtwirc.c includes libtwirc_cmds.c, libtwirc_util.c, libtwirc_evts.c,
        # so compiling the single TU produces the whole library.
        mode = "shared" if self.options.shared else "static"
        if mode == "shared":
            self.run(f"{cc} -g -O0 -o {obj}/libtwirc.o -c -Wall -Werror -fPIC {src}/libtwirc.c")
            # DT_SONAME 供下游链接器按 SONAME 寻址 (L5a 门禁)
            self.run(f"{cc} -shared -Wl,-soname,libtwirc.so {obj}/libtwirc.o -o {self.build_folder}/libtwirc.so")
        else:
            self.run(f"{cc} -c -fPIC -o {obj}/libtwirc.o {src}/libtwirc.c")
            self.run(f"ar rcs {self.build_folder}/libtwirc.a {obj}/libtwirc.o")

    def package(self):
        copy(self, "libtwirc.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        for ext in ("so", "a"):
            copy(self, f"libtwirc.{ext}", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["twirc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]