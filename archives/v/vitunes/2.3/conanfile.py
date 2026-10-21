#!/usr/bin/env python3
"""Conan recipe for vitunes 2.3 on HarmonyOS (OHOS / aarch64).

vitunes is a curses media indexer and player with vi-like key bindings. It is
built by the plain upstream Makefile (Makefile.linux), consumes taglib through
its C bindings (tag_c.h / libtag_c) and ncurses for the terminal user
interface.

OHOS notes:
  * medailib.c used fts(3) to walk the music directories; the OHOS sysroot has
    neither fts.h nor the fts symbols, so the traversal was rewritten on top of
    the POSIX dirent API (patches/0001).
  * e_commands.c stored getopt(3)'s return value in a plain `char`; `char` is
    unsigned on aarch64, so the -1 sentinel never matched and every e-command
    with options (check/flush/tag) aborted with a usage error. The variable is
    an `int` now (patches/0002).
  * upstream links -lncurses/-lutil; the ncurses dependency provides the
    wide-character static libraries and libutil is not referenced by the
    sources, so the link line is composed from the Conan dependencies.
  * the C++ runtime is linked statically so the produced binary only needs
    libc.so at run time.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class VitunesConan(ConanFile):
    name = "vitunes"
    version = "2.3"
    description = "vitunes - a curses media indexer and player with vi-like key bindings"
    license = "ISC"
    homepage = "https://github.com/ryanflannery/vitunes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libtag_c + tag_c.h (the C bindings vitunes uses) are only shipped by
        # the taglib 1.x line: taglib/2.3 is configured with BUILD_BINDINGS=OFF
        # and provides no C wrapper.
        self.requires("taglib/1.13.1")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cxx_runtime_archives(self):
        """Absolute paths of the static libc++ runtime archives.

        Asking the compiler keeps this independent of the SDK layout (the
        archive directory differs between worker images).
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = str(compilers.get("c", "") or "clang")
        archives = []
        for name in ("libc++.a", "libc++abi.a", "libunwind.a"):
            out = subprocess.run([cc, f"-print-file-name={name}"],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 universal_newlines=True)
            path = out.stdout.strip()
            if path and os.path.isfile(path):
                archives.append(path)
            else:
                self.output.warning(f"static {name} not found via {cc}")
        return archives

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan conf, never from the shell env
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = str(compilers.get("c", "") or "clang")

        include_dirs = []
        lib_dirs = []
        for dep in ("taglib", "ncurses", "zlib"):
            cpp_info = self.dependencies[dep].cpp_info
            # package level includedirs first: taglib declares
            # ["include", "include/taglib"] there (vitunes includes <tag_c.h>),
            # while the aggregated component view only reports "include"
            for directory in list(cpp_info.includedirs) + list(cpp_info.aggregated_components().includedirs):
                if directory not in include_dirs:
                    include_dirs.append(directory)
            for directory in cpp_info.aggregated_components().libdirs:
                if directory not in lib_dirs:
                    lib_dirs.append(directory)

        cflags = ["-c", "-std=gnu99", "-D_GNU_SOURCE", "-fPIC",
                  "-Wall", "-Wextra", "-Wno-unused-value"]
        cflags.extend(f"-I{d}" for d in include_dirs)

        ldflags = [f"-L{d}" for d in lib_dirs]
        # tag_c must precede tag (static archives, dependency order first)
        ldflags.extend(["-lm", "-lncursesw", "-ltag_c", "-ltag", "-lz"])
        ldflags.extend(self._cxx_runtime_archives())

        # R9: always -j1
        self.run(f"make -f Makefile.linux CC='{cc}' "
                 f"CFLAGS='{' '.join(cflags)}' "
                 f"LDFLAGS='{' '.join(ldflags)}' -j1",
                 cwd=self.source_folder)

    def package(self):
        # upstream `make install` uses /usr/bin/install with absolute
        # /usr/local paths, so the artifacts are copied directly
        copy(self, "vitunes", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vitunes.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # R38: CLI tool - the binary is the public surface
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
