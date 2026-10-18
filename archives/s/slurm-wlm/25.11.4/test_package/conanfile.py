#!/usr/bin/env python3
"""Conan test package for slurm-wlm: builds a C consumer that links libslurm
and drives the public hostlist API (see test_slurm.c)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SlurmWlmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMakeDeps leaves the generated include/lib variables empty for
        # package_type="application" packages (knowledge DRAFT-12592-...-
        # application-pkgtype-strips-cppinfo), so the consumer is pointed at
        # the installed tree explicitly.  The package has to stay
        # "application": a "library"/static package makes AutotoolsToolchain
        # pass `--disable-shared --enable-static`, which drops slurm's
        # loadable plugin modules and breaks the lib_ref.la links (see the
        # recipe comment and reports/test-report.md §4.4).
        try:
            dep = self.dependencies["slurm-wlm"]
            inc = os.path.join(dep.package_folder, "include")
        except Exception:
            inc = ""
        tc.variables["SLURM_INCLUDE_DIR"] = inc
        tc.variables["SLURM_LIBRARY"] = os.path.join(
            dep.package_folder, "lib", "libslurm.a")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_slurm")
        self.run(exe, env="conanrun")
