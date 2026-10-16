#!/usr/bin/env python3
"""Conan recipe for trimadap 0.1-4.

trimadap is a small C command-line tool built by a plain Makefile. It aligns
every read against each Illumina adapter with a striped Smith-Waterman kernel
(ksw.c) and masks the adapter-derived bases with 'X'.

Upstream ships only the SSE2 kernel, which includes <emmintrin.h> and therefore
does not compile off x86. patches/0001 keeps the SSE2 code path untouched for
x86/x64 and adds an equivalent scalar kernel for aarch64 (OHOS).

The package ships the `trimadap-mt` executable only; kthread.c is linked
statically into that binary.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TrimadapConan(ConanFile):
    name = "trimadap"
    version = "0.1-4"
    description = "Fast but inaccurate adapter trimmer for Illumina reads"
    license = "MIT"
    homepage = "https://github.com/lh3/trimadap"
    url = "https://github.com/lh3/trimadap"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"trimadap supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _dependency_paths(self, dependency, field):
        paths = []
        for path in getattr(dependency.cpp_info, field, []):
            paths.append(
                path
                if os.path.isabs(path)
                else os.path.join(dependency.package_folder, path)
            )
        return paths

    def build(self):
        apply_conandata_patches(self)

        # The upstream Makefile has no CPPFLAGS/LDFLAGS hooks, so the zlib
        # include and library paths are passed through CC/CFLAGS, the same way
        # the seqtk recipe (another plain-Makefile lh3 tool) does it.
        zlib = self.dependencies["zlib"]
        include_flags = [f"-I{p}" for p in self._dependency_paths(zlib, "includedirs")]
        library_flags = [f"-L{p}" for p in self._dependency_paths(zlib, "libdirs")]

        optimization_flags = {
            "Debug": "-g -O0",
            "Release": "-O2",
            "RelWithDebInfo": "-g -O2",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")
        cflags = (
            f"{optimization_flags} -Wall -Wno-unused-function "
            + " ".join(include_flags)
        )

        # R33: the compiler comes from the Conan conf, never from a bare shell
        # variable such as $CC (empty on CI workers -> silent build failure).
        compiler = self._compiler()
        if library_flags:
            compiler = f"{compiler} {' '.join(library_flags)}"

        self.run(f'make -j1 CC="{compiler}" CFLAGS="{cflags}"', cwd=self.source_folder)

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.exists(path):
            return

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.exists(sign_tool):
            os.chmod(path, 0o755)
            return

        signed = path + ".signed"
        if os.path.exists(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}" || true',
                quiet=True,
            )
        self.run(
            f'"{sign_tool}" sign -inFile "{path}" -outFile "{signed}" -selfSign 1',
            quiet=True,
        )
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package(self):
        copy(
            self,
            "trimadap-mt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_elf(os.path.join(self.package_folder, "bin", "trimadap-mt"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
