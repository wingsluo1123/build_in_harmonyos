#!/usr/bin/env python3
"""Consume Qt through its published CMake and build/run environments."""

import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class QtbaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        make = self.conf.get("tools.gnu:make_program", default=None)
        if make and "Makefiles" in tc.generator:
            tc.cache_variables["CMAKE_MAKE_PROGRAM"] = str(make).replace("\\", "/")
        # Same EGL/GLESv2 wiring as the parent recipe: Qt's FindEGL/FindGLESv2
        # do not search the OHOS sysroot on their own, and the OpenGL-enabled
        # Qt6Gui publishes a GLESv2 config dependency that must resolve here.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("cpp") or ""
        if cc:
            import os as _os
            native = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.realpath(cc))))
            sysroot = _os.path.join(native, "sysroot")
            if _os.path.isdir(sysroot):
                include = _os.path.join(sysroot, "usr", "include")
                for arch in ("aarch64-linux-ohos", "arm-linux-ohos"):
                    libdir = _os.path.join(sysroot, "usr", "lib", arch)
                    if _os.path.isdir(libdir):
                        egl = _os.path.join(libdir, "libEGL.so")
                        gles = _os.path.join(libdir, "libGLESv2.so")
                        if _os.path.isfile(egl) and _os.path.isfile(gles):
                            tc.cache_variables["EGL_INCLUDE_DIR"] = include
                            tc.cache_variables["EGL_LIBRARY"] = egl
                            tc.cache_variables["GLESv2_INCLUDE_DIR"] = include
                            tc.cache_variables["GLESv2_LIBRARY"] = gles
                        break
        tc.presets_build_environment = build_env.environment()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            command = [sys.executable, os.path.join(self.source_folder, "run_tests.py"),
                       "--bin-dir", os.path.abspath(self.cpp.build.bindirs[0]),
                       "--log-dir", os.path.join(self.build_folder, "consumer-logs"),
                       "--require-aarch64"]
            if os.environ.get("QTBASE_RUN_WAYLAND_TESTS") == "1":
                command.append("--wayland")
            # QStandardPaths::RuntimeLocation must resolve for the system
            # case; conanrun REPLACES the host env, so inject the runtime
            # dir on the command line instead of relying on inheritance.
            xdg = os.path.join(self.build_folder, "xdg-runtime")
            os.makedirs(xdg, mode=0o700, exist_ok=True)
            command = ["env", f"XDG_RUNTIME_DIR={xdg}"] + command
            self.run(shlex.join(command), env="conanrun")
