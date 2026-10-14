#!/usr/bin/env python3
"""Conan recipe — id3lib 3.8.3 (ID3v1/ID3v2 tag library + CLI tools).

Upstream: SourceForge official project (2003-era autotools; configure was
generated with autoconf 2.13). Builds the static libid3.a plus four CLI
tools (id3info/id3tag/id3convert/id3cp).

HarmonyOS PC (aarch64, os=OHOS) adaptation notes (details in notes.md):

  * config.guess/config.sub patched for the HarmonyOS (ohos) host triplet
    (E007/E072); the platform's `uname -s` is "HarmonyOS".
  * The 2003 configure requires the pre-standard <iomanip.h> header via a
    fatal AC_CHECK_HEADERS; the check is dropped (code uses <iomanip>).
  * Legacy C++ fixes: main() first parameter must be int; <iostream.h>
    replaced by <iostream>; test_io.cpp gains using std::cin/hex/dec.
  * HMDFS + config.status mktemp/umask 077 permission failure (E011):
    umask normalized to 022 in configure and zlib/configure.
  * Uses the registry static zlib/1.3.1 (R18/R26): generate() and build()
    explicitly inject its -I/-L search paths (AutotoolsToolchain does not
    inject dependency paths here), otherwise -lz resolves to the SDK
    sysroot libz.so instead of the packaged libz.a (audit finding).
  * examples/findeng.cpp + findstr.cpp carry a stray CRLF on line 5;
    build() normalizes them before applying the generated patches
    (mp3val/0.1.8 precedent).
"""
import configparser
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Id3LibConan(ConanFile):
    name = "id3lib"
    version = "3.8.3"
    description = ("ID3v1/ID3v2 tag library (C++) with id3info/id3tag/"
                   "id3convert/id3cp CLI tools")
    license = "LGPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/id3lib/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def _zlib_prefix_dirs(self):
        # R26/R18: search paths of the registry static zlib/1.3.1 (private
        # package prefix). AutotoolsToolchain does not inject dependency
        # -I/-L here, so both generate() and build() add them explicitly
        # (id3v2/0.1.12 precedent for the same dependency).
        zlib = self.dependencies["zlib"]
        return (os.path.join(zlib.package_folder, "include"),
                os.path.join(zlib.package_folder, "lib"))

    def source(self):
        # Multi-mirror SourceForge URLs + explicit filename + per-URL retry
        # (gptfdisk/1.0.10 precedent; balancer truncation observed).
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=3, retry_wait=15)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # R26: force the packaged static zlib (libz.a) for configure checks
        # and all links; without -L the SDK sysroot libz.so wins over -lz.
        zlib_inc, zlib_lib = self._zlib_prefix_dirs()
        tc.extra_cflags.append("-I%s" % zlib_inc)
        tc.extra_cxxflags.append("-I%s" % zlib_inc)
        tc.extra_ldflags.append("-L%s" % zlib_lib)
        tc.generate()

    def build(self):
        # Upstream examples/findeng.cpp + findstr.cpp use mixed line
        # terminators (stray CRLF on line 5); normalize to LF before the
        # generated patches are applied (mp3val/0.1.8 precedent).
        self.run("sed -i 's/\\r$//' examples/findeng.cpp examples/findstr.cpp",
                 cwd=self.source_folder)
        apply_conandata_patches(self)

        # E386 class (cdo/2.6.3 + idutils/4.6 + id3v2/0.1.12 precedents): the
        # OHOS profile [buildenv] exports SHELL/CONFIG_SHELL=<hnp bash>. The
        # autoconf 2.13 configure script re-executes itself via $CONFIG_SHELL;
        # the hnp bash cannot resolve its cwd in this environment, so every
        # relative conftest write/`cd ..` inside configure fails
        # ("confdefs.h file not found") and configure aborts with
        #   C preprocessor "<...>" fails sanity check.
        # Run configure with the device /bin/sh and explicit preprocessor
        # commands (R33: compiler paths come from Conan conf, never shell).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        build_conf = configparser.ConfigParser()
        build_conf.read(os.path.join(self.generators_folder, "conanbuild.conf"))
        configure_args = build_conf.get("toolchain", "configure_args", fallback="")
        configure = os.path.join(self.source_folder, "configure").replace("\\", "/")
        # R26: run configure with the packaged zlib headers on CPPFLAGS too
        # (AC_CHECK_HEADERS uses CPPFLAGS; AC_CHECK_LIB uses LDFLAGS which the
        # toolchain env already carries from generate()).
        zlib_inc, _zlib_lib = self._zlib_prefix_dirs()
        self.run(
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh CPP="{cc} -E" '
            f'CXXCPP="{cxx} -E" CPPFLAGS="-I{zlib_inc} $CPPFLAGS" '
            f'"{configure}" {configure_args}',
            cwd=self.build_folder,
        )

        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # Upstream has no TESTS=; make check only builds the 9 check_PROGRAMS.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = ["id3"]
        # R38 (audit): autotools.install() places the 4 upstream CLI tools
        # under bin/; declare bindirs so L0k/PF8 detect the tool surface
        # (commands.json lives at the software level).
        self.cpp_info.bindirs = ["bin"]
