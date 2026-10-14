#!/usr/bin/env python3
"""Test package for gravit/0.5.1 — consumer verification of the installed
application.

Upstream ships no test suite at all (see MANIFEST.yml for the counting
evidence), so the complemented consumer cases carry the validation instead.
They genuinely exercise the installed ``bin/gravit`` and the GL stack it
renders through (R34).  Each test file is a set of **named end-to-end consumer
cases** (rule12), not an assertion list:

* ``test_cli.py`` — 5 CLI consumer cases (``CLI-1``..``CLI-5``): the real
  command-line interface, each case compared byte for byte against an
  independently sourced reference output.
* ``test_headless_render.py`` — 3 consumer cases (``HD-1``..``HD-3``): a real
  headless run (offscreen context, frames, screenshot, self-quit) plus an
  independent PNG decode of the screenshot and a frame-content check.
* ``test_gl_stack.c`` — 3 consumer cases (``GS-1``..``GS-3``) driving the same
  offscreen GL stack (OSMesa + GLU + SDL software surface + libpng) directly.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

# The simulator has no window system to talk to: it renders offscreen and only
# needs a windowless SDL video driver.
_RUN_ENV = {
    "SDL_VIDEODRIVER": "dummy",
    "SDL_AUDIODRIVER": "dummy",
}


class GravitTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv is required: the packaged binary has no RUNPATH for the
    # consumer's cache layout, so the run environment has to supply the library
    # search path (same requirement as the glu/achilles test packages).
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The probe below drives the stack the application renders through;
        # mesa is required directly so its GL/OSMesa headers are exported.
        self.requires("glu/9.0.3")
        self.requires("mesa/24.3.4.1")
        self.requires("sdl12-compat/1.2.68")
        self.requires("libpng/1.6.58")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("gravit is an OHOS-only package and cannot be "
                                 "validated on this host")

        dependency = self.dependencies[self.tested_reference_str]
        package_folder = dependency.package_folder
        executable = os.path.join(package_folder, "bin", "gravit")
        if not os.path.isfile(executable):
            raise ConanException(f"installed command missing: {executable}")

        environment = Environment()
        for key, value in _RUN_ENV.items():
            environment.define(key, value)

        with environment.vars(self).apply():
            # ── 1. CLI consumer cases CLI-1..CLI-5 (no video backend needed) ──
            self.run(
                f'"{sys.executable}" "{os.path.join(self.recipe_folder, "test_cli.py")}"'
                f' "{executable}"',
                env="conanrun",
            )

            # ── 2. Headless consumer cases HD-1..HD-3 (offscreen GL + PNG) ──
            self.run(
                f'"{sys.executable}"'
                f' "{os.path.join(self.recipe_folder, "test_headless_render.py")}"'
                f' "{executable}" "{package_folder}"',
                env="conanrun",
            )

            # ── 3. Consumer cases GS-1..GS-3 of the offscreen GL stack ──
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_gl_stack"),
                env="conanrun",
            )
