#!/usr/bin/env python3
"""Conan test_package — libmtd 2.3.1-3 consumer test (L1).

Builds test.c directly with the compiler resolved by the build environment
and links the packaged static archives through the resolved cpp_info.
Direct compilation (instead of CMake/pkg-config) is deterministic on the
OHOS worker, where pkg-config injection is unreliable.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class LibmtdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC") or "clang"

        inc_dirs, lib_dirs, libs = [], [], []
        for dep in self.dependencies.values():
            ci = dep.cpp_info
            inc_dirs.extend(ci.includedirs)
            lib_dirs.extend(ci.libdirs)
            libs.extend(ci.libs)
            for comp in ci.components.values():
                inc_dirs.extend(comp.includedirs)
                lib_dirs.extend(comp.libdirs)
                libs.extend(comp.libs)

        # de-duplicate while preserving order (dependent libs must precede
        # their deps: libmtd.a references libmissing.a symbols)
        def _uniq(seq):
            seen, out = set(), []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        inc_dirs = _uniq(inc_dirs)
        lib_dirs = _uniq(lib_dirs)
        libs = _uniq(libs)

        inc = " ".join("-I%s" % p for p in inc_dirs)
        lib = " ".join("-L%s" % p for p in lib_dirs)
        lnk = " ".join("-l%s" % l for l in libs)
        cmd = "{cc} test.c -o test_libmtd {inc} {lib} {lnk}".format(
            cc=cc, inc=inc, lib=lib, lnk=lnk)
        self.run(cmd, shell=True, env="conanbuild")

    def test(self):
        self.run("./test_libmtd", env="conanrun")
