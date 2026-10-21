#!/usr/bin/env python3
"""Conan test_package for wlopm 1.0.0 — consumer smoke test.

wlopm is a CLI tool with NO upstream test suite (single C file, no
test/ dir, no unit tests — see test_package/MANIFEST.yml audit).
The consumer smoke cases exercise the packaged bin/wlopm:
  --version / -v, --help / -h (usage text), --json help coverage.
Both markers are emitted from the test_package phase stdout.
"""
import os

from conan import ConanFile


class WlopmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # wlopm NEEDED libwayland-client.so.0 — declare the runtime dep so
        # CMakeDeps/VirtualBuildEnv resolve it and test() can locate the lib.
        self.requires("wayland/1.22.0")

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["wlopm"]
        bindir = dep.cpp_info.bindirs[0]
        bindir = bindir if os.path.isabs(bindir) else os.path.join(
            dep.package_folder, bindir)
        wayland = self.dependencies["wayland"]
        libdir = None
        for d in wayland.cpp_info.libdirs:
            libdir = d if os.path.isabs(d) else os.path.join(
                wayland.package_folder, d)
            break
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        if libdir:
            ld = libdir + (":" + ld if ld else "")
        os.environ["LD_LIBRARY_PATH"] = ld
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        binpath = os.path.join(bindir, "wlopm")
        self.run(f'{bash} test.sh "{binpath}"', env="conanbuild")
