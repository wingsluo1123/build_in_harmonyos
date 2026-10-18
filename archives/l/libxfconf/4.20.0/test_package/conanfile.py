#!/usr/bin/env python3
"""Conan test_package for libxfconf 4.20.0 — HarmonyOS consumer test.

Compiles and runs a third-party consumer of the installed package:

  * header closure: libxfconf-0 (include/xfce4/xfconf-0) + the GLib closure
    pulled in by libxfconf's public headers (glib-2.0 / gobject-2.0 / gio-2.0
    / gthread-2.0, plus the gio-unix header directory)
  * link line: -lxfconf-0 -lgio-2.0 -lgobject-2.0 -lglib-2.0 -lintl -lm
    -lpthread -ldl.  -lintl is mandatory under OHOS lld because it defaults to
    --no-allow-shlib-undefined and glib's proxy libintl (SONAME libintl.so.8)
    is the only provider of the g_libintl_* symbols referenced by libglib-2.0.

Deliberately no CMakeDeps/component-name indirection: the link line is spelled
out so a CI failure points at the artifact, not at a generator property.
R33: the compiler comes from Conan's tools.build:compiler_executables conf, the
shell ${CC} variable is never used.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class LibxfconfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _collect_paths(self):
        incs = []
        libdirs = []
        for _ref, dep in self.dependencies.items():
            if dep.package_folder is None:
                continue
            dirs = list(dep.cpp_info.includedirs)
            for _name, comp in dep.cpp_info.components.items():
                dirs += list(comp.includedirs)
            for path in dirs:
                if not path:
                    continue
                if not os.path.isabs(path):
                    path = os.path.join(dep.package_folder, path)
                if path not in incs:
                    incs.append(path)
            for path in dep.cpp_info.libdirs:
                if not path:
                    continue
                if not os.path.isabs(path):
                    path = os.path.join(dep.package_folder, path)
                if path not in libdirs:
                    libdirs.append(path)
            # gio-unix-2.0 is a header-only subdirectory of the glib package and
            # has no cpp_info component, so add it explicitly.
            gio_unix = os.path.join(dep.package_folder, "include", "gio-unix-2.0")
            if os.path.isdir(gio_unix) and gio_unix not in incs:
                incs.append(gio_unix)
        return incs, libdirs

    def build(self):
        incs, libdirs = self._collect_paths()
        inc_flags = " ".join("-I" + d for d in incs)
        lib_flags = " ".join("-L" + d for d in libdirs)

        conf = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}
        cc = conf.get("c") or "clang"

        self.run(
            f"{cc} test.c -o test_libxfconf {inc_flags} {lib_flags} "
            f"-lxfconf-0 -lgio-2.0 -lgobject-2.0 -lglib-2.0 "
            f"-lintl -lm -lpthread -ldl"
        )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run: compile+link verified")
            return
        self.run("./test_libxfconf", env="conanrun")
