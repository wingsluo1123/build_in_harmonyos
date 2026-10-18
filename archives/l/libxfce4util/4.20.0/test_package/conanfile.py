#!/usr/bin/env python3
"""Conan consumer test for libxfce4util 4.20.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Libxfce4utilTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross build: consumer execution skipped")
            return
        dep = self.dependencies["libxfce4util"]
        pkg_folder = dep.package_folder

        # Installed face: the canonical upstream pkg-config module ships with
        # the package and declares the exact release version.
        pc_path = os.path.join(pkg_folder, "lib", "pkgconfig", "libxfce4util-1.0.pc")
        assert os.path.isfile(pc_path), "missing installed pkg-config module: {}".format(pc_path)
        with open(pc_path, "r", encoding="utf-8", errors="ignore") as handle:
            pc_text = handle.read()
        assert "Version: 4.20.0" in pc_text, "libxfce4util-1.0.pc version mismatch"
        self.output.info("installed face: libxfce4util-1.0.pc Version 4.20.0 confirmed")

        # Consumer binary cases (compile+link against the packaged shared
        # library, execute under the OHOS loader).
        test_bin = os.path.join(self.cpp.build.bindirs[0], "libxfce4util_consumer")
        cases = ("version", "ohos-guard", "fileutils-roundtrip")
        for case in cases:
            self.run(
                '"{}" {}'.format(test_bin, case),
                env="conanrun",
                cwd=self.build_folder,
            )

        # Shipped CLI tool: proves the packaged executable resolves
        # libxfce4util.so.7 and its glib closure on the OHOS dynamic loader
        # (post-package ELF processing kept the artifacts loadable).
        # Upstream installs it via sbin_PROGRAMS, but Conan's
        # AutotoolsToolchain flattens --sbindir to ${prefix}/bin.
        kiosk = os.path.join(pkg_folder, "bin", "xfce4-kiosk-query")
        assert os.path.isfile(kiosk), "missing installed xfce4-kiosk-query"
        self.run('"{}" -v'.format(kiosk), env="conanrun")
