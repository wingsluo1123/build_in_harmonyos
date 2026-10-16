#!/usr/bin/env python3
"""Conan test_package for wlogout 1.2.2 — consumer smoke test.

wlogout is a GUI application with NO upstream test suite (no tests/
dir, no test() in meson.build — see test_package/MANIFEST.yml audit).
The consumer smoke cases exercise the packaged bin/wlogout:
  --version / -v (prints "wlogout <version>"), --help / -h (usage).
"""
import os

from conan import ConanFile


class WlogoutTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # wlogout links the gtk stack; declare it so the test runner can
        # locate the runtime shared libraries.
        self.requires("gtk/3.24.43")

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["wlogout"]
        bindir = dep.cpp_info.bindirs[0]
        bindir = bindir if os.path.isabs(bindir) else os.path.join(
            dep.package_folder, bindir)
        # wlogout links the whole GTK stack transitively (gobject/pango/
        # cairo/gdk-pixbuf/...); the OHOS loader ignores DT_RUNPATH, so
        # EVERY dependency's lib dir must be on LD_LIBRARY_PATH (a gtk-only
        # path leaves libgobject-2.0.so.0 unresolved — local repro).
        libdirs = []
        for d in self.dependencies.values():
            if not getattr(d, "package_folder", None):
                continue
            for libdir in (d.cpp_info.libdirs or []):
                if not libdir:
                    continue
                resolved = libdir if os.path.isabs(libdir) else os.path.join(
                    d.package_folder, libdir)
                if os.path.isdir(resolved):
                    libdirs.append(resolved)
        ld = ":".join(libdirs)
        prev = os.environ.get("LD_LIBRARY_PATH", "")
        if prev:
            ld = ld + ":" + prev
        os.environ["LD_LIBRARY_PATH"] = ld
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        binpath = os.path.join(bindir, "wlogout")
        self.run(f'{bash} test.sh "{binpath}"', env="conanbuild")
