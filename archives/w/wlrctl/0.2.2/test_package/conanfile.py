#!/usr/bin/env python3
"""Conan test_package for wlrctl 0.2.2 — consumer smoke test.

wlrctl is a CLI tool with NO upstream test suite (no test/ dir, no
*test* source, no meson test()/benchmark() — see
test_package/MANIFEST.yml audit). The consumer smoke cases exercise
the packaged bin/wlrctl along argument-parsing paths that terminate
BEFORE wl_display_connect — no Wayland session required:
--version / -v, --help / -h (usage), no-arg usage, unknown command,
and the keyboard/pointer/toplevel/output argument-validation error
paths. Both markers are emitted from the test_package phase stdout.
"""
import os

from conan import ConanFile


class WlrctlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # wlrctl NEEDED libwayland-client.so.0 + libxkbcommon.so.0 —
        # declare the runtime deps so VirtualBuildEnv resolves them and
        # test() can locate the libs.
        self.requires("wayland/1.22.0")
        self.requires("libxkbcommon/1.13.1")

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["wlrctl"]
        bindir = dep.cpp_info.bindirs[0]
        bindir = bindir if os.path.isabs(bindir) else os.path.join(
            dep.package_folder, bindir)
        lib_dirs = []
        for name in ("wayland", "libxkbcommon"):
            d = self.dependencies[name]
            for ld in d.cpp_info.libdirs:
                lib_dirs.append(ld if os.path.isabs(ld) else os.path.join(
                    d.package_folder, ld))
                break
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        if lib_dirs:
            ld = ":".join(lib_dirs) + (":" + ld if ld else "")
        os.environ["LD_LIBRARY_PATH"] = ld
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        binpath = os.path.join(bindir, "wlrctl")
        self.run(f'{bash} test.sh "{binpath}"', env="conanbuild")
