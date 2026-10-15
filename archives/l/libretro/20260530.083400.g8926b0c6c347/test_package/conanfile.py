#!/usr/bin/env python3
"""Conan test_package — libretro 20260530.083400.g8926b0c6c347 (libretro core).

Consumer-style L1 tests: compile test.c (consumer smoke: public retro_* ABI)
and test_ohos.c (HarmonyOS lifecycle: retro_set_environment ->
retro_init -> retro_get_system_info -> retro_deinit on the OHOS runtime,
assertion-free), then dlopen the installed yabause_libretro.so and exercise
both.
"""
import os

from conan import ConanFile


class LibretroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libretro"]
        libdir = dep.cpp_info.libdirs[0]
        core = os.path.join(libdir, "yabause_libretro.so")
        # Redirect compiler output to a file and echo it back: when conan's
        # stdout is a pipe, toolchain invocations writing to the inherited
        # pipe can fail in constrained sandboxes with no diagnostic; a file
        # makes failures fast and logged.
        self.run(
            "clang test.c -o test_libretro -ldl > compile-test.log 2>&1; "
            "rc=$?; cat compile-test.log; exit $rc",
            env="conanbuild",
        )
        self.run(
            "clang test_ohos.c -o test_libretro-ohos -ldl > compile-ohos.log 2>&1; "
            "rc=$?; cat compile-ohos.log; exit $rc",
            env="conanbuild",
        )
        # Record the packaged core path for the test() runs
        self._core_path = core

    def test(self):
        core = self._core_path
        self.run(f"./test_libretro '{core}'", env="conanrun")
        self.run(f"./test_libretro-ohos '{core}'", env="conanrun")
