#!/usr/bin/env python3
"""test_package for oath-toolkit — verifies liboath HOTP/TOTP generation API."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building


class OathToolkitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkgconfig(self, what):
        """Run pkg-config to get --cflags or --libs for oath-toolkit."""
        pc_name = "oath-toolkit"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for cand in ("/data/service/hnp/bin/pkg-config", "/usr/bin/pkg-config"):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    exe = cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, pc_name], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def build(self):
        dep = self.dependencies["oath-toolkit"].cpp_info
        # Gather include flags from pkg-config and cpp_info
        incs = []
        pc_cflags = self._pkgconfig("--cflags")
        if pc_cflags:
            incs.extend(pc_cflags.split())
        # Also check transitive deps for include paths
        for ref, d in self.dependencies.items():
            base = getattr(d, "package_folder", None) or ""
            for p in d.cpp_info.includedirs:
                if not os.path.isabs(p) and base:
                    p = os.path.join(base, p)
                if os.path.isdir(p):
                    incs.append("-I" + p)
        inc = " ".join(dict.fromkeys(incs))

        # Gather lib flags
        libdirs = []
        for ref, d in self.dependencies.items():
            libdirs += d.cpp_info.libdirs
        pc_libs = self._pkgconfig("--libs")
        libs = pc_libs.split() if pc_libs else ["-l" + l for l in dep.libs]
        link = " ".join(["-L" + p for p in libdirs] + libs
                        + ["-Wl,-rpath," + p for p in libdirs])

        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "-fPIC -O2")
        src = os.path.join(self.source_folder, "test.c")
        self.run(f"{cc} {cflags} {inc} -c {src} -o test.o", env="conanbuild")
        self.run(f"{cc} {cflags} {link} -o test_oath_toolkit test.o", env="conanbuild")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Build LD_LIBRARY_PATH from all deps
        libdirs = []
        for ref, d in self.dependencies.items():
            libdirs += d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        # Also add SDK lib path so lld's libxml2 doesn't conflict
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        ldpath = sdk_lib + os.pathsep + ldpath
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_oath_toolkit'",
            env="conanrun"
        )
