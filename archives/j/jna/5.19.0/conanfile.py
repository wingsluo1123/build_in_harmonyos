#!/usr/bin/env python3
"""Conan recipe for JNA (Java Native Access) native library.

JNA's native component (libjnidispatch.so) is a C library that provides
the bridge between Java and native shared libraries via libffi.

This recipe builds only the native C code (dispatch.c, callback.c) and
statically links libffi to produce a self-contained libjnidispatch.so
that only depends on libc.so at runtime.

JNI headers (jni.h, jni_md.h, com_sun_jna_*.h) are bundled as source
files since no Conan package for JDK headers exists.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, mkdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JnaConan(ConanFile):
    name = "jna"
    version = "5.19.0"
    description = "Java Native Access - native JNI library for calling native shared libraries"
    license = "Apache-2.0 / LGPL-2.1+"
    homepage = "https://github.com/java-native-access/jna"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*.h"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libffi/3.4.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        native_dir = os.path.join(self.source_folder, "native")
        build_dir = os.path.join(self.build_folder, "build")
        mkdir(self, build_dir)

        # Copy JNI headers from exported sources to native directory
        # exports_sources places files either at source root or patches/ subdir
        jni_headers = [
            "jni.h", "jni_md.h",
            "com_sun_jna_Function.h",
            "com_sun_jna_Native.h",
            "com_sun_jna_win32_DLLCallback.h",
        ]
        for header in jni_headers:
            # Try source root first, then patches/ subdir
            src_root = os.path.join(self.source_folder, header)
            src_patches = os.path.join(self.source_folder, "patches", header)
            src = src_root if os.path.exists(src_root) else src_patches
            if os.path.exists(src):
                copy(self, header, os.path.dirname(src), native_dir)

        # Get compiler from Conan conf (R33: never use shell env vars)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # Get libffi dependency info
        ffi = self.dependencies["libffi"]
        ffi_package = ffi.package_folder
        ffi_include = os.path.join(ffi_package, "include")
        ffi_lib_dir = os.path.join(ffi_package, "lib")
        ffi_static_lib = os.path.join(ffi_lib_dir, "libffi.a")

        # Compile flags
        cflags = " ".join([
            "-fPIC", "-O2", "-fno-omit-frame-pointer", "-fno-strict-aliasing",
            "-DHAVE_PROTECTION", "-DNO_JAWT", "-D_REENTRANT",
            '-DJNA_JNI_VERSION=\\"7.0.4\\"',
            '-DCHECKSUM=\\"5fb98531302accd485c534c452dd952a\\"',
            "-W", "-Wall", "-Wno-unused", "-Wno-parentheses",
            "-Wno-implicit-function-declaration",
            f"-I{native_dir}",
            f"-I{ffi_include}",
        ])

        # Compile dispatch.c
        self.run(f"{cc} {cflags} -c {os.path.join(native_dir, 'dispatch.c')} "
                 f"-o {os.path.join(build_dir, 'dispatch.o')}")

        # Compile callback.c
        self.run(f"{cc} {cflags} -c {os.path.join(native_dir, 'callback.c')} "
                 f"-o {os.path.join(build_dir, 'callback.o')}")

        # Link libjnidispatch.so (static libffi, only depends on libc.so)
        self.run(f"{cc} -shared -o {os.path.join(build_dir, 'libjnidispatch.so')} "
                 f"{os.path.join(build_dir, 'dispatch.o')} "
                 f"{os.path.join(build_dir, 'callback.o')} "
                 f"{ffi_static_lib} "
                 f"-Wl,-soname,libjnidispatch.so,-Bsymbolic "
                 f"-ldl -lm")

        # Compile test libraries
        self.run(f"{cc} {cflags} -c {os.path.join(native_dir, 'testlib.c')} "
                 f"-o {os.path.join(build_dir, 'testlib.o')}")
        self.run(f"{cc} -shared -o {os.path.join(build_dir, 'libtestlib.so')} "
                 f"{os.path.join(build_dir, 'testlib.o')} -ldl -lm")

        self.run(f"{cc} {cflags} -c {os.path.join(native_dir, 'testlib2.c')} "
                 f"-o {os.path.join(build_dir, 'testlib2.o')}")
        self.run(f"{cc} -shared -o {os.path.join(build_dir, 'libtestlib2.so')} "
                 f"{os.path.join(build_dir, 'testlib2.o')} "
                 f"-L{build_dir} -ltestlib -ldl -lm")

    def package(self):
        build_dir = os.path.join(self.build_folder, "build")
        copy(self, "libjnidispatch.so", build_dir,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libtestlib.so", build_dir,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libtestlib2.so", build_dir,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["jnidispatch"]
        self.cpp_info.includedirs = []
