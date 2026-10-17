#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for libzc.

CI runs this automatically via `conan create` (which invokes test_package).
Two executables are built and run:
  - test_libzc            — real libzc API smoke test (zc_new/zc_file_open/...)
  - harmonyos_ohos_test   — HarmonyOS-specific test that drives zc_crk_bforce,
    exercising the OHOS pthread-cancellation fallback (patch 0001).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibzcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Explicitly prepend every dependency libdir to LD_LIBRARY_PATH:
        # VirtualRunEnv's conanrunenv libdirs can be empty on this runner, and
        # without it the loader cannot find libzc.so.6 (lcalc/libarchive
        # lessons). conanrun env still supplies PATH etc.
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep.cpp_info and getattr(dep.cpp_info, "libdirs", None):
                lib_dirs.extend(str(d) for d in dep.cpp_info.libdirs)
        ldpath = ":".join(lib_dirs) if lib_dirs else ""
        bindir = self.cpp.build.bindirs[0]
        bash = self._ohos_shell() if hasattr(self, "_ohos_shell") else None
        for test in ("test_libzc", "harmonyos_ohos_test"):
            exe = os.path.join(bindir, test)
            if bash:
                cmd = f"{bash} -c 'LD_LIBRARY_PATH=\"{ldpath}\" ./{exe}'"
            else:
                cmd = f"LD_LIBRARY_PATH={ldpath} {exe}"
            self.run(cmd, env="conanrun")
