#!/usr/bin/env python3
"""test_package — obs/32.1.2 consumer test.

Verifies the installed package by compiling and running a small consumer that
links OBS::libobs. The test itself (src/test_obs.c) is HarmonyOS-specific: it
exercises the __OHOS__ os_set_thread_name() path added by the port alongside
version/obs_data/path checks. The four upstream cmocka unit tests are executed
by the recipe's build() step (ctest).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class ObsTestPackage(ConanFile):
    name = "obs-test-package"
    test_type = "explicit"
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # libobs.so is loaded through its direct and transitive dependencies
        # (FFmpeg, X11, ...), so build the runtime search path from every
        # package in the graph rather than relying on the build-tree RPATH.
        libdirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                full = libdir if os.path.isabs(libdir) \
                    else os.path.join(dep.package_folder, libdir)
                if os.path.isdir(full) and full not in libdirs:
                    libdirs.append(full)

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(libdirs))
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_obs"))
