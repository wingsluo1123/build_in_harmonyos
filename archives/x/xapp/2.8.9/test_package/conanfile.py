#!/usr/bin/env python3
"""Conan test_package for xapp 2.8.9 — OHOS-specific consumer test (L1).

Upstream xapp 2.8.9 has no automated test suite (NO_UPSTREAM_TESTS, see
../notes.md), so this package carries bespoke OHOS assertions instead
(test_xapp.c): xapp.pc metadata closure, headless GType registration,
loader/DT_NEEDED + g_libintl proxy-libintl closure, the GDK_WINDOWING_X11
guard-patch evidence in the packaged .so, and a gsettings schema
compile + memory-backend roundtrip. None of them open a display.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class XappTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # ⚠️ Explicit generators replace the conan defaults — VirtualRunEnv must be
    # included or test() cannot source the dependency LD_LIBRARY_PATH.
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # xapp's public headers include gtk/glib; the C test also calls
        # g_settings (gio) directly. gtk/3.24.43 covers the gtk+-3.0/gobject/
        # cairo .pc Requires chain of xapp.pc; libxkbfile/1.1.3 covers the
        # Requires.private: xkbfile member (pkg-config 0.29.2 resolves
        # Requires(.private) strictly, so xkbfile.pc must be locatable).
        self.requires("gtk/3.24.43")
        self.requires("libxkbfile/1.1.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        env = Environment()
        if self.settings.os == "OHOS":
            # OHOS: gtk transitive deps (harfbuzz etc.) NEED libc++_shared.so
            # which the conan graph does not carry — provided by /system/lib64
            # (gtksourceview3/gtksourceview4 test_package precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

        xapp = self.dependencies[self.tested_reference_str]
        so = os.path.join(xapp.package_folder, "lib", "libxapp.so.1")
        env.define_path("XAPP_SO_PATH", so)
        env.define_path("XAPP_SCHEMA_DIR",
                        os.path.join(xapp.package_folder, "share", "glib-2.0", "schemas"))

        for _ref, dep in self.dependencies.items():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            tool = os.path.join(folder, "bin", "glib-compile-schemas")
            if os.path.isfile(tool):
                env.define_path("XAPP_GLIB_COMPILE_SCHEMAS", tool)
                break

        # Headless gsettings backend: no dconf daemon and no session bus exist
        # on the CI runner; must be set before the first GSettings call.
        env.define("GSETTINGS_BACKEND", "memory")
        env.vars(self).save_script("xapp_test_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run the test binary in this environment")
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_xapp")
        self.run(bin_path, env=["conanrun", "xapp_test_env"], cwd=self.build_folder)
