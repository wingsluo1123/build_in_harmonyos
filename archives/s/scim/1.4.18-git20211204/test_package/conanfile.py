#!/usr/bin/env python3
"""Conan test_package for scim — consumer smoke test.

Uses pkg-config + direct clang++ (no CMake): the HNP cmake binary cannot load
libc++_shared.so inside the conan subprocess environment (manual shell works,
conan's CMake helper does not), so a plain compile+link+run probe is the
reliable path — same pattern as libthai.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # PkgConfigDeps so pkg-config can find the generated .pc files.
    # VirtualRunEnv / VirtualBuildEnv must both be present: being explicit
    # with generators *replaces* (not appends to) the conan default set; losing
    # VirtualRunEnv means test() gets no conanrun env (no LD_LIBRARY_PATH) and
    # the probe fails at runtime with "Error loading shared library".
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkgconfig(self, what):
        pc = "scim"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + \
            env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for cand in ("/data/service/hnp/bin/pkg-config", "/usr/bin/pkg-config"):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    exe = cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, pc], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _pkgconfig_cflags(self):
        out = self._pkgconfig("--cflags")
        if not out:
            self.output.warning("pkg-config --cflags 取不到，回退 cpp_info")
        return out

    def _all_libdirs(self):
        libdirs = []
        for _ref, dep in self.dependencies.items():
            libdirs += dep.cpp_info.libdirs
        return list(dict.fromkeys(libdirs))

    def build(self):
        dep = self.dependencies["scim"].cpp_info
        inc = self._pkgconfig_cflags()
        if not inc:
            incs = []
            for _ref, d in self.dependencies.items():
                for p in d.cpp_info.includedirs:
                    incs.append("-I" + p)
            inc = " ".join(dict.fromkeys(incs))
        libdirs = self._all_libdirs()
        pcl = self._pkgconfig("--libs")
        libs = pcl.split() if pcl else ["-l" + l for l in dep.libs]
        link = " ".join(["-L" + p for p in libdirs] + libs
                        + ["-Wl,-rpath," + p for p in libdirs])
        cxx = os.environ.get("CXX", "clang++")
        # musl needs the gnu dialect so POSIX/wide-string helpers are declared.
        self.run(f"{cxx} -std=gnu++17 test.cpp -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        libdirs = self._all_libdirs()
        if str(self.settings.os) == "OHOS":
            # clang++-built probe links OHOS libc++; its loader path lives in
            # the SDK <llvm>/lib/aarch64-linux-ohos which the profile does not
            # add to LD_LIBRARY_PATH (same fix as the main recipe).
            tools = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            compiler = tools.get("c", "clang")
            real_clang = os.path.realpath(compiler)
            llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(real_clang)), "lib",
                "aarch64-linux-ohos")
            if os.path.isdir(llvm_lib):
                libdirs = list(dict.fromkeys(libdirs + [llvm_lib]))
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
            f"./test_probe'",
            env="conanrun")