#!/usr/bin/env python3
"""Consumer test for imagination/3.6 (HarmonyOS PC, aarch64).

imagination is a GTK+3 GUI application.  The assertions live in
imagination_consumer_test.c (a real C source, per CI L0c) and cover:

1. packaged-binary contract — bin/imagination is a genuine aarch64 ELF;
2. transition-plugin inventory — all 15 packaged GModule plugins under
   lib/imagination/ dlopen cleanly on the OHOS loader and honour the
   img_get_plugin_info() contract (non-empty group, NULL-terminated
   name/symbol/id triplet array);
3. headless entrypoint smoke — the binary resolves its whole GTK+3
   shared-library closure and stops exactly at GTK display
   initialisation ("Cannot open display"), never at a dynamic-link
   failure (l3afpad precedent: a GUI binary can only be asserted up to
   display init on a headless device).

env="conanrun" puts the dependency graph's libdirs on LD_LIBRARY_PATH,
which both the dlopen() calls and the exec'd binary need.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ImaginationTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["imagination"]
        binary = os.path.join(dep.cpp_info.bindirs[0], "imagination")
        plugin_dir = os.path.join(dep.cpp_info.libdirs[0], "imagination")
        test_bin = os.path.join(self.cpp.build.bindir, "imagination_consumer_test")
        # The GTK+3 closure pulled in by libharfbuzz needs libc++_shared.so,
        # which lives in the platform system runtime dir /system/lib64 —
        # not on the loader's default search path on the build host (the
        # ohos-aarch64 profile prepends the same dir for the sign tool).
        # The inline prefix keeps the conanrun dependency libdirs (needed
        # for libgtk-3 and friends) right behind the system runtime; on a
        # real device /system/lib64 is a default loader path anyway.
        self.run(
            'LD_LIBRARY_PATH="/system/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
            '"%s" "%s" "%s"' % (test_bin, plugin_dir, binary),
            env="conanrun")
