#!/usr/bin/env python3
"""Conan test_package - papi 7.2.0 (direct-cc consumer test for OHOS).

Builds test_papi.c directly with the profile compiler instead of CMake.
CMake has no Platform/HarmonyOS module and its compiler check fails on
the worker (CMake Error at project(), CMAKE_C_COMPILER ...). Direct-cc
uses the same conanbuild env (CC/sysroot) as the main recipe, links the
packaged libpapi, runs test_papi (emits HMBS_TEST_PACKAGE_RESULT) plus
papi_version via absolute path (VirtualRunEnv does not put the tested
package bin/ on PATH).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PapiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_cc(self):
        # Same fingerprint as main-recipe _resolve_compiler (Error 77) but
        # in test_package context: profile pins
        # tools.build:compiler_executables to /data/service/hnp/bin/clang,
        # which is inaccessible on some workers
        # (/bin/sh: ... inaccessible or not found, Error 127). Probe the
        # pinned path; fall back to PATH/sibling lookup and finally bare
        # "clang" resolved via conanbuild PATH at self.run time (HMBS
        # front-loads tool dirs). Flags untouched; CC only.
        import shutil
        import subprocess
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 check_type=dict, default={})
        except Exception:
            exes = {}
        pinned = exes.get("c") if isinstance(exes, dict) else None

        def _works(exe):
            try:
                if not exe or not os.path.isfile(exe):
                    return False
                p = subprocess.run([exe, "--version"], capture_output=True,
                                   text=True, timeout=15)
                return p.returncode == 0
            except Exception:
                return False

        if pinned and _works(pinned):
            self.output.info("papi test_package: pinned CC works: %s" % pinned)
            return pinned
        if pinned:
            self.output.warning("papi test_package: pinned CC unusable: %s; "
                                "falling back via PATH lookup" % pinned)
            try:
                d = os.path.dirname(pinned)
                if d:
                    cand = os.path.join(d, "clang")
                    if _works(cand):
                        self.output.info("papi test_package: sibling CC: %s"
                                         % cand)
                        return cand
            except Exception:
                pass
        found = shutil.which("clang")
        if found and _works(found):
            self.output.info("papi test_package: PATH CC: %s" % found)
            return found
        if found:
            return found
        # Last resort: bare name resolved via conanbuild PATH at run time.
        self.output.warning("papi test_package: no probed CC; using bare clang")
        return "clang"

    def build(self):
        cc = self._resolve_cc()
        includes = []
        libdirs = []
        libs = []
        for dep in self.dependencies.values():
            includes.extend(dep.cpp_info.includedirs)
            libdirs.extend(dep.cpp_info.libdirs)
            libs.extend(dep.cpp_info.libs)
        inc_flags = " ".join('"%s"' % ("-I%s" % i) for i in includes)
        lib_flags = " ".join('"%s"' % ("-L%s" % d) for d in libdirs)
        link_libs = " ".join("-l%s" % lib for lib in libs)
        src = os.path.join(self.source_folder, "test_papi.c")
        out = os.path.join(self.build_folder, "test_papi")
        self.run('%s -O2 %s -o "%s" "%s" %s %s -lm -pthread'
                 % (cc, inc_flags, out, src, lib_flags, link_libs),
                 env="conanbuild")

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_papi")
            self.run('"%s"' % test_bin, env="conanrun")
            dep = self.dependencies["papi"]
            raw_bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
            if os.path.isabs(raw_bindir):
                papi_version = os.path.join(raw_bindir, "papi_version")
            else:
                papi_version = os.path.join(dep.package_folder, raw_bindir,
                                            "papi_version")
            self.run('"%s"' % papi_version, env="conanrun")
