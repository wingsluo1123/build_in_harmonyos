#!/usr/bin/env python3
"""Conan test_package — lasem 0.6.0 (consumer test).

Builds test_lasem.c against the installed lasem package via CMakeDeps
and runs it with the conanrun environment: the binary parses inline
MathML/SVG documents from memory, performs layout (pango text shaping)
and renders onto cairo ARGB32 surfaces, plus exercises the DOM
implementation API. Exit code 0 == consumer verification PASS.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LasemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, configured, names):
        # Prefer the profile-configured compiler when it exists on disk;
        # otherwise fall back to PATH + well-known true-machine locations.
        # Preflight proved the CI profile pins /data/service/hnp/bin/clang
        # which is absent on the real machine (resolved there to
        # ~/.harmonybrew/bin/clang); main-recipe _resolve_compilers does
        # the same rewrite for meson, this mirrors it for CMakeToolchain.
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        for base in (os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                     "/storage/Users/currentUser/usr/local/bin",
                     "/storage/Users/currentUser/.harmonybrew/bin",
                     os.path.expanduser("~/.harmonybrew/bin"),
                     "/data/service/hnp/bin"):
            for name in names:
                cand = os.path.join(base, name)
                if os.path.isfile(cand):
                    return cand
        return configured or names[0]

    def generate(self):
        tc = CMakeToolchain(self)
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
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # The cache_variables pin alone did not override the stale profile
        # compiler on the true device (zydis 4.1.1 precedent), so rewrite
        # the generated conan_toolchain.cmake when the configured path is
        # missing and the resolved one exists, and export CC/CXX.
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
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
            else:
                self.output.warning(
                    "HMBS diag test toolchain not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag test toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning(
                "HMBS diag test compiler env failed: %s" % e)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile+link only")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_lasem")
        log_path = os.path.join(self.build_folder, "test_lasem.log")
        run_ok = True
        try:
            self.run('"%s" > "%s" 2>&1' % (binary, log_path), env="conanrun")
        except Exception as e:
            run_ok = False
            self.output.warning("test_lasem run failed: %s" % e)
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError as e:
            self.output.warning("cannot read test log %s: %s" % (log_path, e))
            out = ""
        for line in out.splitlines()[-25:]:
            self.output.info("[test_lasem] %s" % line)
        if not out.strip():
            self.output.warning("test_lasem produced empty output")
        # Falsification guard: binary must be a real non-empty ELF.
        if os.path.isfile(binary) and os.path.getsize(binary) == 0:
            raise RuntimeError("test binary is empty: %s" % binary)
        # Single deterministic count source: the final summary line
        # (no stdout word counting, no arithmetic patch-ups, no
        # returncode override of counts).
        m = re.search(r"=====\s+(\d+)/(\d+)\s+assertions passed\s+=====", out)
        if not m:
            fail_marker = {
                "executed": True,
                "passed": False,
                "command": "./test_lasem (3 scenes, 16 assertions)",
                "discovered": 16,
                "passedCount": 0,
            }
            self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
                fail_marker, separators=(",", ":")))
            raise RuntimeError(
                "test_lasem left no parseable summary line; searched for "
                "'===== N/M assertions passed =====' in %s" % log_path)
        passed_count = int(m.group(1))
        discovered = int(m.group(2))
        if not (0 <= passed_count <= discovered and discovered > 0):
            self.output.warning(
                "HMBS diag count identity broken: passedCount=%d discovered=%d"
                % (passed_count, discovered))
        ok = run_ok and passed_count == discovered and discovered > 0
        marker = {
            "executed": True,
            "passed": bool(ok),
            "command": "./test_lasem (3 scenes, 16 assertions)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
            marker, separators=(",", ":")))
        self._reemit_upstream()
        if not ok:
            raise RuntimeError(
                "test_lasem failed: %d/%d passed (run_ok=%s)"
                % (passed_count, discovered, run_ok))

    def _reemit_upstream(self):
        # Re-emit the upstream result persisted in the package res/ so
        # cache-hit rounds still provide evidence every round
        # (laz-perf 3.4.0 precedent).
        try:
            dep_name = self.tested_reference_str.split("/")[0]
        except Exception:
            dep_name = "lasem"
        try:
            dep = self.dependencies[dep_name]
        except Exception as e:
            self.output.warning("upstream re-emit lookup failed: %s" % e)
            raise RuntimeError("hmbs_upstream.json absent: no dep %s" % dep_name)
        cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
        if not os.path.isfile(cand):
            self.output.warning(
                "hmbs_upstream.json absent from package res/; upstream "
                "marker left to the main build (cache-miss rounds)")
            raise RuntimeError("hmbs_upstream.json not found in package")
        with open(cand, "r", encoding="utf-8") as f:
            up = json.load(f)
        ok_shape = (
            isinstance(up, dict)
            and up.get("status") in ("passed", "failed")
            and up.get("framework") == "meson"
            and isinstance(up.get("discovered"), int)
            and isinstance(up.get("executed"), int)
            and isinstance(up.get("passed"), int)
            and isinstance(up.get("failed"), int)
            and isinstance(up.get("skipped"), int)
            and up["passed"] + up["failed"] == up["executed"]
            and up["executed"] + up["skipped"] <= up["discovered"]
        )
        self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            up, separators=(",", ":")))
        if not ok_shape:
            raise RuntimeError("upstream test evidence invalid: %s" % up)
