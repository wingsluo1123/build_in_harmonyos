#!/usr/bin/env python3
"""Conan test_package for oneDPL 2022.12.0.

Builds test_onedpl.cpp against the packaged headers (onedpl::onedpl target)
and runs it. Emits the HMBS_TEST_PACKAGE_RESULT marker; the 10/10 counts are
the explicit runtime checks in test_onedpl.cpp.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class OnedplTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # Mirror main recipe: redirect temp root away from read-only /tmp.
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.getenv("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                tmpdir = json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                os.environ["GOTMPDIR"] = cand
                return cand
            except Exception:
                continue
        return None

    def _resolve_compiler(self, configured, names):
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("GOTMPDIR", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")
        # E092 applies to the consumer too: without this pin the test
        # binary configures as unknown Platform/HarmonyOS (same failure as
        # the main recipe). Pattern verified by vvenc test_package.
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag test compilers c=%s cxx=%s" % (_c, _cxx))
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        # Same stale-path correction as main recipe (zydis evidence).
        try:
            pairs = []
            c_old = _compilers.get("c")
            cxx_old = _compilers.get("cpp")
            if c_old and _c and c_old != _c \
                    and not os.path.exists(c_old) and os.path.exists(_c):
                pairs.append((c_old, _c))
            if cxx_old and _cxx and cxx_old != _cxx \
                    and not os.path.exists(cxx_old) and os.path.exists(_cxx):
                pairs.append((cxx_old, _cxx))
            if pairs:
                gf = getattr(self, "generators_folder", None)
                path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
                if path and os.path.isfile(path):
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        text = f.read()
                    orig = text
                    for old_p, new_p in pairs:
                        text = text.replace(old_p, new_p)
                    if text != orig:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(text)
                        self.output.info(
                            "HMBS diag test fixed toolchain %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag test toolchain fix failed: %s" % e)

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        stats = {
            "executed": True,
            "passed": True,
            "command": "./test_onedpl",
            "discovered": 10,
            "passedCount": 10,
        }
        exe = os.path.join(self.cpp.build.bindirs[0], "test_onedpl")
        try:
            self.run(exe, env="conanrun")
        except Exception:
            stats["passed"] = False
            stats["passedCount"] = 0
            stats["gaps"] = [{
                "count": 10,
                "category": "test_failure",
                "detail": "test_onedpl exited non-zero; see test output above for the failing [check N] line",
                "evidence": "conan create test_package phase stdout (./test_onedpl FAIL line)",
            }]
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(stats, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(stats, ensure_ascii=False))
