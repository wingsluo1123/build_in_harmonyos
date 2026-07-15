#!/usr/bin/env python3
"""Conan recipe for libmpack 1.0.3 — MessagePack serialization library.

Build system: Makefile (uses libtool, but we build directly without libtool
since it's not available on OHOS).
"""
import os

from conan import ConanFile, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibmpackConan(ConanFile):
    name = "libmpack"
    version = "1.0.3"
    description = "Small binary serialization library implementing msgpack and msgpack-rpc formats"
    license = "MIT"
    homepage = "https://github.com/libmpack/libmpack"
    url = "https://github.com/libmpack/libmpack"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration("libmpack only supports static linking")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # libmpack uses a Makefile with libtool, but libtool is not available
        # on OHOS. Build directly: create amalgamation header, compile sources,
        # create static library.
        # R33: compiler from Conan conf, never from shell env vars
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        cc = executables.get("c", "clang")
        ar = executables.get("ar", "llvm-ar")

        src = self.source_folder
        build_dir = os.path.join(src, "build")

        # Create build directory
        os.makedirs(build_dir, exist_ok=True)

        # Create amalgamation header (concat all headers, removing internal includes)
        hdrs = ["src/core.h", "src/conv.h", "src/object.h", "src/rpc.h"]
        amalg_h = os.path.join(build_dir, "mpack.h")
        with open(amalg_h, "w") as f:
            for h in hdrs:
                path = os.path.join(src, h)
                with open(path) as hf:
                    for line in hf:
                        if not line.startswith('#include "'):
                            f.write(line)

        # Compile each source file
        # Adjust optimization flags based on build_type
        build_type = str(self.settings.build_type) if self.settings.build_type else "Release"
        if build_type == "Debug":
            opt_flags = "-O0 -g"
        elif build_type == "RelWithDebInfo":
            opt_flags = "-O2 -g"
        else:
            opt_flags = "-O2"
        cflags = f"-fPIC {opt_flags} -Wall -Wextra -std=c99 -I{build_dir}"
        sources = ["core.c", "conv.c", "object.c", "rpc.c"]
        objects = []
        for s in sources:
            obj = os.path.join(build_dir, s.replace(".c", ".o"))
            obj_dir = os.path.dirname(obj)
            os.makedirs(obj_dir, exist_ok=True)
            self.run(f'{cc} {cflags} -c {os.path.join(src, "src", s)} -o {obj}')
            objects.append(obj)

        # Create static library
        lib_path = os.path.join(build_dir, "libmpack.a")
        self.run(f'{ar} rcs {lib_path} {" ".join(objects)}')

    def package(self):
        src = self.source_folder
        copy(self, "mpack.h", src=os.path.join(src, "build"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libmpack.a", src=os.path.join(src, "build"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["mpack"]
