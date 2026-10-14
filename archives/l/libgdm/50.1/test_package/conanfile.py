#!/usr/bin/env python3
"""Conan test_package for libgdm 50.1.

Compiles and links a real consumer against libgdm (via the generated gdm.pc
plus glib/gio/gobject modules) and executes the probe binary — proving the
library, its headers and its runtime deps all resolve on HarmonyOS PC.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building


class LibgdmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkgconfig(self, what):
        """Run pkg-config for the modules libgdm needs."""
        modules = "gdm gio-2.0 gobject-2.0 glib-2.0"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for cand in ("/data/service/hnp/bin/pkg-config",
                         "/storage/Users/currentUser/usr/local/bin/pkg-config",
                         "/usr/bin/pkg-config"):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    exe = cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what] + modules.split(),
                                 capture_output=True, text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def build(self):
        dep = self.dependencies["libgdm"].cpp_info
        inc = self._pkgconfig("--cflags")
        link = self._pkgconfig("--libs")
        if not inc or not link:
            # fallback to cpp_info aggregation (should not happen with PkgConfigDeps)
            incs, libdirs, libs = [], [], []
            for _ref, _d in self.dependencies.items():
                for _p in _d.cpp_info.includedirs:
                    incs.append("-I" + _p)
                libdirs += _d.cpp_info.libdirs
                libs += _d.cpp_info.libs
            inc = " ".join(dict.fromkeys(incs))
            link = " ".join(["-L" + p for p in dict.fromkeys(libdirs)]
                            + ["-l" + l for l in dict.fromkeys(libs)]
                            + ["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} -std=gnu99 test.c -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_probe'",
                 env="conanrun")
