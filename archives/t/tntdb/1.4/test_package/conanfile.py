#!/usr/bin/env python3
"""Conan test_package — tntdb 1.4.

Builds test_tntdb.cpp (real public APIs against a local sqlite file DB:
connect, DDL/DML, selectValue/selectRow/select, placeholder binding,
transaction rollback, Value/Decimal/SqlBuilder) with CMake and runs it
via ctest. Emits HMBS_TEST_PACKAGE_RESULT with the real check count
(10 CHECKs; TNTEST_RESULT summary + process exit status).

True-machine note (HMBS readonly_tmp): /tmp is read-only on the device.
The test DB is created under TMPDIR (see test_tntdb.cpp), and ctest runs
with the probe-verified writable root exported; only the temp root is
redirected, no test is skipped. The sqlite driver (tntdb5-sqlite.so)
ships inside the package lib/ dir, found through the conanrun library
path — no extra driver path setup needed.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


def _resolve_writable_tmp(build_folder):
    def _is_path_cand(v):
        if not v or v in ("0", "1", "/tmp"):
            return False
        return os.path.isabs(v)
    for cand in (os.environ.get("TMPDIR"), os.environ.get("TMP"), os.environ.get("TEMP")):
        if not _is_path_cand(cand):
            continue
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".hmbs_probe")
            with open(probe, "w", encoding="utf-8") as _pf:
                _pf.write("probe")
            os.remove(probe)
            return cand
        except Exception:
            continue
    fallback = os.path.join(build_folder, ".tmp")
    os.makedirs(fallback, exist_ok=True)
    return fallback


class TntdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_tntdb.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Consumer test includes tntdb public headers that include
        # <cxxtools/smartptr.h>; declare the dep explicitly so CMakeDeps
        # always generates the cxxtools config in this context (same
        # version as the main recipe requirements()).
        self.requires("cxxtools/3.0.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # True device migrated clang from /data/service/hnp/bin to
        # ~/usr/local/bin, but the shared profile still points at the old
        # path (main-recipe _pin_real_compilers precedent; this round's
        # failure: CMAKE_CXX_COMPILER /data/service/hnp/bin/clang++ broken).
        # Resolve working compilers and pin them into the toolchain cache
        # plus a build-scope env script; then rewrite any stale absolute
        # path leaked into already-generated files.
        try:
            _conf = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            _conf = None
        if not isinstance(_conf, dict):
            _conf = {}
        def _resolve(_configured, _names):
            if _configured and os.path.isfile(_configured):
                try:
                    if os.access(_configured, os.X_OK):
                        return _configured
                except Exception:
                    return _configured
                return _configured
            for _n in _names:
                try:
                    _f = shutil.which(_n)
                except Exception:
                    _f = None
                if _f:
                    return _f
            for _base in (os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                          "/storage/Users/currentUser/usr/local/bin",
                          "/usr/local/bin", "/usr/bin", "/bin"):
                for _n in _names:
                    _c = os.path.join(_base, _n)
                    if os.path.isfile(_c):
                        return _c
            return _configured or _names[0]
        _c_old = _conf.get("c")
        _cxx_old = _conf.get("cpp")
        _c = _resolve(_c_old, ("clang", "cc", "gcc"))
        _cxx = _resolve(_cxx_old, ("clang++", "c++", "g++"))
        self.output.info("HMBS diag test compilers configured c=%s cxx=%s" % (_c_old, _cxx_old))
        self.output.info("HMBS diag test compilers resolved c=%s cxx=%s" % (_c, _cxx))
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if _c and os.path.isfile(str(_c)):
            tc.cache_variables["CMAKE_C_COMPILER"] = str(_c)
        if _cxx and os.path.isfile(str(_cxx)):
            tc.cache_variables["CMAKE_CXX_COMPILER"] = str(_cxx)
        tc.generate()
        _pairs = []
        if _c_old and _c and _c_old != _c and not os.path.isfile(str(_c_old)) and os.path.isfile(str(_c)):
            _pairs.append((str(_c_old), str(_c)))
        if _cxx_old and _cxx and _cxx_old != _cxx and not os.path.isfile(str(_cxx_old)) and os.path.isfile(str(_cxx)):
            _pairs.append((str(_cxx_old), str(_cxx)))
        if _pairs:
            try:
                _env = Environment()
                for _old, _new in _pairs:
                    if _old == _c_old:
                        _env.define("CC", _new)
                    if _old == _cxx_old:
                        _env.define("CXX", _new)
                _env.vars(self, scope="build").save_script("hmbs_test_compiler")
                self.output.info("[ok] OHOS port: pinned real CC/CXX for test_package")
            except Exception as _e:
                self.output.warning("test compiler env export failed: %s" % _e)
            try:
                _gf = str(getattr(self, "generators_folder", "") or "")
                if _gf and os.path.isdir(_gf):
                    for _fn in os.listdir(_gf):
                        if not (_fn.endswith(".cmake") or _fn.endswith(".sh") or _fn.endswith(".presets.json")):
                            continue
                        _p = os.path.join(_gf, _fn)
                        try:
                            with open(_p, "r", encoding="utf-8", errors="replace") as _f:
                                _t = _f.read()
                        except OSError:
                            continue
                        _orig = _t
                        for _old, _new in _pairs:
                            if _old in _t:
                                _t = _t.replace(_old, _new)
                        if _t != _orig:
                            try:
                                with open(_p, "w", encoding="utf-8", newline="\n") as _f:
                                    _f.write(_t)
                                self.output.info("[ok] OHOS port: fixed stale compiler in test %s" % _fn)
                            except OSError as _e:
                                self.output.warning("fix test %s failed: %s" % (_fn, _e))
            except Exception as _e:
                self.output.warning("test generator patch failed: %s" % _e)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _dep_lib_dirs(self):
        dirs = []
        try:
            for _req, dep in self.dependencies.items():
                try:
                    _pf = dep.package_folder
                except Exception:
                    continue
                if not _pf:
                    continue
                cand = os.path.join(_pf, "lib")
                if os.path.isdir(cand) and cand not in dirs:
                    dirs.append(cand)
        except Exception as _e:
            self.output.warning("dep lib dir scan failed: %s" % _e)
        return dirs

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile+link check only")
            return
        # readonly_tmp gate: resolve a probe-verified writable root and
        # export it both to os.environ and as explicit VAR="..." prefixes
        # (env="conanrun" aggregation may shadow plain os.environ).
        tmpdir = _resolve_writable_tmp(self.build_folder)
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self.output.info("[ok] OHOS port: test_package TMPDIR=%s" % tmpdir)
        # Ordered expectation set, same order as test_tntdb.cpp main().
        # Used ONLY to name gaps (which CHECK never printed); no assertion
        # logic is changed and counts come solely from CHECK lines.
        expected = ["selectValue-max", "selectRow-fields",
                    "select-cursor-count", "statement-bind",
                    "transaction-rollback", "value-convert", "value-null",
                    "decimal-scale", "sqlbuilder-select", "connection-alive"]
        discovered = 10
        cmd = "ctest -V -R test_tntdb"
        # Run ctest via subprocess so its combined output can be parsed
        # deterministically (single source: CHECK lines). self.run() would
        # only give rc, forcing the forbidden rc==0 guess branch.
        # NOTE: must be -V, not --output-on-failure. The latter suppresses
        # the test's stdout on success, so a fully passing binary yields
        # zero CHECK lines and the parser reports a bogus 0/10 failure
        # (CI #85029: ctest exit=0 Passed yet marker read passedCount=0).
        # -V always prints test output, so CHECK lines are visible both
        # on pass and on failure; counts still come solely from CHECK.
        run_env = dict(os.environ)
        run_env["TMPDIR"] = tmpdir
        run_env["TMP"] = tmpdir
        run_env["TEMP"] = tmpdir
        lib_dirs = []
        for _sub in ("lib",):
            _c = os.path.join(self.build_folder, _sub)
            if os.path.isdir(_c) and _c not in lib_dirs:
                lib_dirs.append(_c)
        try:
            _bf = str(getattr(self, "build_folder", "") or "")
            if _bf and os.path.isdir(_bf):
                for _root, _ds, _fs in os.walk(_bf):
                    if os.path.basename(_root) == "build":
                        continue
        except Exception:
            pass
        lib_dirs.extend([d for d in self._dep_lib_dirs() if d not in lib_dirs])
        _ld = run_env.get("LD_LIBRARY_PATH", "")
        run_env["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([_ld] if _ld else []))
        _hmbs_cmake = os.environ.get("HMBS_CMAKE", "")
        _ctest_cands = []
        try:
            if _hmbs_cmake and os.path.isfile(_hmbs_cmake):
                _ctest_cands.append(os.path.join(os.path.dirname(_hmbs_cmake), "ctest"))
        except Exception:
            pass
        ctest = ""
        for _cc in _ctest_cands:
            if _cc and os.path.isfile(_cc):
                ctest = _cc
                break
        if not ctest:
            ctest = shutil.which("ctest") or "ctest"
        proc = None
        output = ""
        try:
            proc = subprocess.run(
                [ctest, "-V", "-R", "test_tntdb"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=1200, cwd=self.build_folder, env=run_env)
            output = proc.stdout or ""
        except Exception as _e:
            output = "DIAG ctest spawn failed: %s" % _e
            self.output.error(output)
        try:
            self.output.info("ctest exit=%s tail:\n%s" % (
                proc.returncode if proc is not None else "spawn-failed",
                output[-4000:]))
        except Exception:
            pass
        # Single deterministic source: CHECK PASS/FAIL lines. TNTEST_RESULT
        # and ctest summary are evidence only, never overwrite counts.
        # NOTE: under ctest -V every test-output line carries a numeric
        # prefix (CI 89106: lines look like "1: CHECK PASS: ...");
        # strip it before matching so the parser works in both -V
        # and --output-on-failure modes. Counts still come solely
        # from CHECK lines.
        def _norm(_ln):
            _t = _ln.strip()
            return re.sub("^\d+:\s*", "", _t)
        pass_names = []
        fail_names = []
        try:
            for _ln in output.splitlines():
                _s = _norm(_ln)
                _m = re.match(r"^CHECK\s+(PASS|FAIL):\s*(\S+)\s*$", _s)
                if _m:
                    if _m.group(1) == "PASS":
                        pass_names.append(_m.group(2))
                    else:
                        fail_names.append(_m.group(2))
        except Exception as _e:
            self.output.warning("CHECK parse failed: %s" % _e)
        # Deduplicate preserving order (binary prints each once).
        seen = set()
        uniq_pass = []
        for _n in pass_names:
            if _n not in seen:
                seen.add(_n)
                uniq_pass.append(_n)
        seen_f = set(uniq_pass)
        uniq_fail = []
        for _n in fail_names:
            if _n not in seen_f and _n not in uniq_fail:
                uniq_fail.append(_n)
        passed = len(uniq_pass)
        # Identity self-check: passed + failed == executed-side accounting.
        # Missing = expected names never printed (early abort); they are
        # failures with setup/abort evidence, not skips.
        printed = set(uniq_pass) | set(uniq_fail)
        missing = [_n for _n in expected if _n not in printed]
        failed = discovered - passed
        # Collect per-name evidence: DIAG lines + TNTEST_RESULT + tail.
        diag_by_name = {}
        tntest_line = ""
        try:
            for _ln in output.splitlines():
                _s = _norm(_ln)
                if _s.startswith("DIAG "):
                    # DIAG <name> ...  or DIAG setup ...
                    _parts = _s.split(None, 2)
                    if len(_parts) >= 2:
                        _k = _parts[1]
                        diag_by_name.setdefault(_k, []).append(_s[:300])
                if _s.startswith("TNTEST_RESULT"):
                    tntest_line = _s[:200]
        except Exception:
            pass
        test_pkg = {
            "executed": True,
            "passed": passed == discovered,
            "command": cmd,
            "discovered": discovered,
            "passedCount": passed,
        }
        if passed != discovered:
            gaps = []
            for _n in uniq_fail:
                _ev = "; ".join(diag_by_name.get(_n, [])[:2])
                if tntest_line:
                    _ev = (_ev + "; " + tntest_line)[:500] if _ev else tntest_line
                if not _ev:
                    _ev = "ctest output tail: " + (output[-500:] if output else "empty")
                gaps.append({
                    "count": 1,
                    "category": "test_failure",
                    "detail": "%s: consumer CHECK FAIL" % _n,
                    "evidence": ("test_tntdb %s -> CHECK FAIL; %s" % (_n, _ev))[:800],
                })
            for _n in missing:
                _ev = "; ".join(diag_by_name.get(_n, [])[:2])
                _setup = "; ".join(diag_by_name.get("setup", [])[:1])
                if _setup and not _ev:
                    _ev = _setup
                if tntest_line:
                    _ev = (_ev + "; " + tntest_line)[:500] if _ev else tntest_line
                if not _ev:
                    _ev = "ctest output tail: " + (output[-500:] if output else "empty")
                gaps.append({
                    "count": 1,
                    "category": "test_failure",
                    "detail": "%s: no CHECK line (aborted before reporting)" % _n,
                    "evidence": ("test_tntdb %s -> missing CHECK; %s" % (_n, _ev))[:800],
                })
            # Hard invariant: sum(gaps.count) == failed. No guessing fixup;
            # if the parser is inconsistent, report the accounting instead
            # of fabricating numbers.
            _sum = sum(int(_g.get("count", 0)) for _g in gaps)
            if _sum != failed:
                self.output.warning(
                    "gap accounting mismatch sum=%d failed=%d "
                    "(passed=%d discovered=%d)" % (_sum, failed, passed, discovered))
            if gaps:
                test_pkg["gaps"] = gaps
        _tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
        try:
            print(_tp_marker, flush=True)
        except Exception:
            pass
        self.output.info(_tp_marker)
        # Re-emit the real upstream evidence every round: on Conan cache-hit
        # rounds build() is skipped so its marker never appears in this run's
        # stdout. The file below is the measured test/tntdb-test -s result
        # shipped with the package; only re-emit, never synthesize.
        try:
            _up = None
            try:
                _pkg_folder = self.dependencies["tntdb"].package_folder
            except Exception:
                _pkg_folder = None
            if _pkg_folder:
                _c = os.path.join(_pkg_folder, "res", "hmbs_upstream.json")
                try:
                    if os.path.isfile(_c):
                        with open(_c, "r", encoding="utf-8") as _f:
                            _up = json.load(_f)
                        self.output.info("[ok] OHOS port: re-emitting upstream evidence from %s" % _c)
                except Exception:
                    pass
            if isinstance(_up, dict) and int(_up.get("discovered", 0)) > 0:
                _um = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_up, ensure_ascii=False)
                try:
                    print(_um, flush=True)
                except Exception:
                    pass
                self.output.info(_um)
            else:
                self.output.warning("hmbs_upstream.json missing in package; upstream evidence only from build() this round")
        except Exception as _e:
            self.output.warning("re-emit upstream evidence failed: %s" % _e)
        if passed != discovered:
            raise ConanException("test_package consumer tests failed")
