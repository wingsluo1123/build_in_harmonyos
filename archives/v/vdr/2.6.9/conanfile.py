#!/usr/bin/env python3
"""Conan recipe — vdr 2.6.9 (Video Disk Recorder).

VDR is a digital video recorder for DVB-S/C/T cards. It uses a hand written
GNU make build system (`Makefile` + optional `Make.config`), there is no
configure script, no CMake and no meson.

OHOS adaptation notes (see notes.md / manifest.yaml for the full list):

* VDR is written against glibc. Its ioctl/device surface (linux/dvb/*.h) is
  provided by the OHOS sysroot, but a handful of glibc-only helpers
  (__GLIBC_PREREQ, DEFFILEMODE, __compar_fn_t, __attribute_format_arg__,
  malloc_trim) are not, so patches/0001 adds minimal fallbacks.
* The OHOS libc header set has no libcap API (its sys/capability.h only
  declares the raw capget/capset syscalls), so libcap is a real dependency.
* gettext()/adjtime()/pthread_cancel() are exported by the *runtime* musl
  loader but are missing from the SDK link-time libc.so stub; link the loader
  explicitly (same idiom as the glib/abr2gbr recipes).
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

# OHOS: the SDK's link time libc.so stub does not export the gettext family,
# adjtime() or pthread_cancel(); the runtime musl loader does. Linking the
# loader by soname makes those symbols resolvable (glib/abr2gbr precedent).
_MUSL_LINK_ARGS = ["-L/lib", "-l:ld-musl-aarch64.so.1"]

# The SDK ships an empty libintl.h stub (it defines __USE_GNU_GETTEXT but
# declares none of the gettext family), so VDR's i18n.c gets implicit
# declarations. Inject a minimal, prototype-carrying header of the same name.
_LIBINTL_H = """\
#ifndef _LIBINTL_H
#define _LIBINTL_H

#include <locale.h>

#ifdef __cplusplus
extern "C" {
#endif

extern char *gettext(const char *) __attribute__((__format_arg__(1)));
extern char *dgettext(const char *, const char *) __attribute__((__format_arg__(2)));
extern char *dcgettext(const char *, const char *, int) __attribute__((__format_arg__(2)));
extern char *ngettext(const char *, const char *, unsigned long);
extern char *dngettext(const char *, const char *, const char *, unsigned long);
extern char *dcngettext(const char *, const char *, const char *, unsigned long, int);
extern char *bind_textdomain_codeset(const char *, const char *);
extern char *bindtextdomain(const char *, const char *);
extern char *textdomain(const char *);

#ifdef __cplusplus
}
#endif

#endif
"""


class VdrConan(ConanFile):
    name = "vdr"
    version = "2.6.9"
    description = "Video Disk Recorder — digital video recorder for DVB-S/C/T devices"
    license = "GPL-2.0-or-later"
    homepage = "https://www.tvdr.de/"
    url = "https://github.com/vdr-projects/vdr"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # VDR always links -ljpeg -lcap and pulls freetype2/fontconfig via
        # pkg-config (see Makefile).
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libcap/2.78")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _write_libintl_proxy(self):
        path = os.path.join(self.generators_folder, "libintl.h")
        if not os.path.isfile(path):
            os.makedirs(self.generators_folder, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(_LIBINTL_H)

    def _dependency_flags(self):
        """Collect include/lib flags from the whole transitive dependency graph.

        VDR's Makefile asks pkg-config for freetype2/fontconfig and hard codes
        -ljpeg/-lcap; instead of depending on .pc files being generated we pass
        the resolved flags explicitly, which also covers transitive deps.
        """
        includes, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            cpp_info = dep.cpp_info.aggregated_components()
            for directory in cpp_info.includedirs:
                if directory not in includes:
                    includes.append(directory)
            for directory in cpp_info.libdirs:
                if directory not in libdirs:
                    libdirs.append(directory)
            for name in list(cpp_info.libs) + list(cpp_info.system_libs):
                if name not in libs:
                    libs.append(name)
        return includes, libdirs, libs

    def generate(self):
        self._write_libintl_proxy()

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"

        includes, libdirs, libs = self._dependency_flags()
        # Our minimal libintl.h must win over the (empty) SDK stub.
        includes.insert(0, self.generators_folder)

        cincludes = " ".join(f"-I{d}" for d in includes)
        lib_flags = [f"-L{d}" for d in libdirs]
        lib_flags += [f"-l{name}" for name in libs]
        lib_flags += _MUSL_LINK_ARGS
        libs_line = " ".join(lib_flags)

        # Only the `vdr` target is built: `all` additionally builds the
        # translations (needs xgettext/msgfmt) and the bundled demo plugins
        # (skincurses needs ncurses), neither of which belongs to the recorder
        # binary this package ships. See notes.md.
        self.run(
            f'make -j1 VERBOSE=1 -C "{self.source_folder}" vdr '
            f'CC="{cc}" CXX="{cxx}" PKG_CONFIG=true '
            f'CINCLUDES="{cincludes}" LIBS="{libs_line}"'
        )

    def package(self):
        copy(
            self,
            "vdr",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "vdr.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "vdr.5",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man5"),
        )
        copy(
            self,
            "svdrpsend.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
