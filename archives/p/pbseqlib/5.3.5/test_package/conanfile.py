#!/usr/bin/env python3
"""Conan test_package for pbseqlib 5.3.5.

Consumer-level verification: build and run test_pbseqlib, which exercises
the public NucConversion tables and the DNASequence API. Emits
HMBS_TEST_PACKAGE_RESULT with the real check counters parsed from the test
binary output, and re-emits the packaged HMBS_UPSTREAM_TEST_RESULT summary.
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PbseqlibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Collect absolute lib dirs now so they can be embedded as RPATH
        # (OHOS loader ignores LD_LIBRARY_PATH; RPATH lives in the binary).
        rpath_dirs = []
        try:
            for _req, dep in self.dependencies.items():
                try:
                    for _d in (dep.cpp_info.libdirs or []):
                        if _d and os.path.isdir(_d) and _d not in rpath_dirs:
                            rpath_dirs.append(_d)
                except Exception:
                    pass
                try:
                    _pkg = dep.package_folder
                except Exception:
                    continue
                if not _pkg or not os.path.isdir(_pkg):
                    continue
                for _sub in ("lib", "lib64"):
                    _d = os.path.join(_pkg, _sub)
                    if os.path.isdir(_d) and _d not in rpath_dirs:
                        rpath_dirs.append(_d)
        except Exception as exc:
            self.output.warning("pbseqlib test build: rpath scan skipped (%s)" % exc)
        self.output.info("pbseqlib test build: rpath_dirs=%s" % (rpath_dirs,))
        cmake = CMake(self)
        _vars = {}
        if rpath_dirs:
            _vars["PBSEQLIB_EXTRA_RPATH"] = ";".join(rpath_dirs)
        # Explicit full-static route: locate the three static archives in
        # this package (libblasr.a guaranteed by the both_libraries
        # normalization; libpbbam.a/libpbcopper.a merged at package time)
        # plus every transitive shared dep file, and hand full paths to
        # CMake. The test binary then carries no DT_NEEDED on libblasr.so
        # at all. Missing inputs fail fast here with searched paths.
        try:
            import glob as _glob2

            _dep = self.dependencies["pbseqlib"]
            _search = []
            try:
                for _d in (_dep.cpp_info.libdirs or []):
                    if _d and os.path.isdir(_d) and _d not in _search:
                        _search.append(_d)
            except Exception:
                pass
            try:
                _pkg = _dep.package_folder
                if _pkg and os.path.isdir(_pkg):
                    for _sub in ("lib", "lib64"):
                        _d = os.path.join(_pkg, _sub)
                        if os.path.isdir(_d) and _d not in _search:
                            _search.append(_d)
            except Exception:
                pass

            def _find_archive(names):
                for _d in _search:
                    for _n in names:
                        _cand = os.path.join(_d, _n)
                        try:
                            if os.path.isfile(_cand) and os.path.getsize(_cand) > 0:
                                return _cand
                        except Exception:
                            continue
                return ""

            _blasr = _find_archive(("libblasr.a",))
            _pbbam = _find_archive(("libpbbam.a",))
            _pbcopper = _find_archive(("libpbcopper.a",))
            self.output.info(
                "pbseqlib test build: static blasr=%s pbbam=%s pbcopper=%s"
                % (_blasr or "<none>", _pbbam or "<none>", _pbcopper or "<none>")
            )
            if _blasr:
                _vars["PBSEQLIB_STATIC_LIB"] = _blasr
            if _pbbam:
                _vars["PBSEQLIB_STATIC_PBBAM"] = _pbbam
            if _pbcopper:
                _vars["PBSEQLIB_STATIC_PBCOPPER"] = _pbcopper
            # Transitive deps as explicit files (direct hdf5/htslib/zlib/boost
            # plus htslib's own xz/libdeflate and any other host dep the
            # static archives reference); system libs as -l flags.
            # Deterministic single source: each dep's cpp_info (plus
            # components), resolved against its own libdirs. Order keeps
            # direct deps first so static dependents (htslib) precede
            # their dependencies (xz/libdeflate/zlib) on the link line.
            _trans = []
            _ordered = []
            _seen_dep = set()
            for _prio in ("hdf5", "htslib", "zlib", "boost", "xz", "libdeflate", "bzip2"):
                if _prio in _seen_dep:
                    continue
                try:
                    _dd0 = self.dependencies[_prio]
                except Exception:
                    continue
                _ordered.append((_prio, _dd0))
                _seen_dep.add(_prio)
            try:
                for _ddv in self.dependencies.values():
                    try:
                        _dn = str(_ddv.ref.name)
                    except Exception:
                        continue
                    if not _dn or _dn in _seen_dep or _dn in ("pbseqlib", "gtest"):
                        continue
                    _ordered.append((_dn, _ddv))
                    _seen_dep.add(_dn)
            except Exception:
                pass
            for _name, _dd in _ordered:
                try:
                    _dd = self.dependencies[_name]
                except Exception:
                    continue
                try:
                    _libdirs = [
                        d for d in (_dd.cpp_info.libdirs or [])
                        if d and os.path.isdir(d)
                    ]
                except Exception:
                    _libdirs = []
                try:
                    _libs = list(_dd.cpp_info.libs or [])
                except Exception:
                    _libs = []
                try:
                    _comp = getattr(_dd.cpp_info, "components", None) or {}
                    _items = _comp.values() if hasattr(_comp, "values") else []
                    for _c in _items:
                        try:
                            for _cl in (getattr(_c, "libs", None) or []):
                                if _cl and _cl not in _libs:
                                    _libs.append(_cl)
                        except Exception:
                            continue
                except Exception:
                    pass
                for _lib in _libs:
                    _found = ""
                    for _d in _libdirs:
                        try:
                            _cands = [
                                c for c in sorted(
                                    _glob2.glob(os.path.join(_d, "lib%s.so*" % _lib))
                                )
                                if os.path.isfile(c)
                            ]
                            if not _cands:
                                _a = os.path.join(_d, "lib%s.a" % _lib)
                                if os.path.isfile(_a):
                                    _cands = [_a]
                            if _cands:
                                # Prefer the unversioned .so when present so
                                # the linker records the canonical SONAME.
                                _cands.sort(key=lambda p: (
                                    os.path.basename(p) != "lib%s.so" % _lib,
                                    len(p),
                                ))
                                _found = _cands[0]
                                break
                        except Exception:
                            continue
                    if _found:
                        if _found not in _trans:
                            _trans.append(_found)
                    else:
                        self.output.warning(
                            "pbseqlib test build: lib %s of dep %s not found "
                            "in %s" % (_lib, _name, _libdirs)
                        )
                try:
                    _sys_all = list(_dd.cpp_info.system_libs or [])
                    try:
                        _comp2 = getattr(_dd.cpp_info, "components", None) or {}
                        _items2 = _comp2.values() if hasattr(_comp2, "values") else []
                        for _c2 in _items2:
                            try:
                                for _sl in (getattr(_c2, "system_libs", None) or []):
                                    if _sl and _sl not in _sys_all:
                                        _sys_all.append(_sl)
                            except Exception:
                                continue
                    except Exception:
                        pass
                    for _s in _sys_all:
                        if _s and "-l%s" % _s not in _trans:
                            _trans.append("-l%s" % _s)
                except Exception:
                    pass
            self.output.info("pbseqlib test build: transitive=%s" % (_trans,))
            if _trans:
                _vars["PBSEQLIB_TRANSITIVE_LIBS"] = ";".join(_trans)
        except Exception as exc:
            self.output.warning("pbseqlib test build: static scan skipped (%s)" % exc)
        # CI #94023 (3rd round on this fingerprint, new route vs the
        # static-linkage/gaps/no-change rounds): the main libblasr build
        # with /data/service/hnp/bin/clang++ already succeeded seconds
        # earlier, then test_package died in CMake's own compiler ABI
        # probe with `posix_spawn failed: Resource temporarily
        # unavailable` before compiling any recipe code. Preset the
        # compiler-works flags so this redundant probe is skipped; the
        # real test binary still compiles+links below, so a truly broken
        # toolchain still fails honestly at cmake.build().
        _vars["CMAKE_CXX_COMPILER_WORKS"] = "1"
        _vars["CMAKE_C_COMPILER_WORKS"] = "1"
        cmake.configure(variables=_vars)
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross build: pbseqlib consumer was built; run it on the "
                "HarmonyOS PC target."
            )
            return
        bindir = self.cpp.build.bindirs[0]
        exe = os.path.join(self.build_folder, bindir, "test_pbseqlib")
        if not os.path.isfile(exe):
            import glob

            hits = glob.glob(
                os.path.join(self.build_folder, "**", "test_pbseqlib*"),
                recursive=True,
            )
            hits = [
                h
                for h in hits
                if os.path.isfile(h)
                and not h.endswith((".o", ".obj", ".cmake", ".make"))
            ]
            for h in hits:
                if os.access(h, os.X_OK) or h.endswith(".exe"):
                    exe = h
                    break
            else:
                if hits:
                    exe = hits[0]
        # Runtime diagnostics: Error 127 here means the loader could not
        # start the binary (missing .so or bad path), not a test failure.
        # Resolve lib dirs from every host dep so a VirtualRunEnv gap does
        # not mask as "command not found"; conanrun env still applies.
        try:
            os.chmod(exe, 0o755)
        except Exception:
            pass
        libdirs = []
        try:
            # Prefer the declared libdirs (handles versioned/cross subdirs
            # such as lib/aarch64-* that a hardcoded lib/lib64 scan misses),
            # then fall back to a prefix walk for any dir holding *.so*.
            for _req, dep in self.dependencies.items():
                try:
                    info = dep.cpp_info
                except Exception:
                    info = None
                seen_pkg = ""
                try:
                    seen_pkg = dep.package_folder
                except Exception:
                    pass
                if info is not None:
                    try:
                        for d in (info.libdirs or []):
                            if d and os.path.isdir(d) and d not in libdirs:
                                libdirs.append(d)
                    except Exception:
                        pass
                try:
                    pkg = seen_pkg
                except Exception:
                    continue
                if not pkg or not os.path.isdir(pkg):
                    continue
                for sub in ("lib", "lib64"):
                    d = os.path.join(pkg, "lib") if sub == "lib" else os.path.join(pkg, sub)
                    if os.path.isdir(d) and d not in libdirs:
                        libdirs.append(d)
                try:
                    for root, _ds, files in os.walk(pkg):
                        if any(
                            f.endswith(".so") or ".so." in f or f.endswith(".a")
                            for f in files
                        ):
                            if root not in libdirs:
                                libdirs.append(root)
                            break
                except Exception:
                    pass
        except Exception as exc:
            self.output.warning("pbseqlib test: libdir scan skipped (%s)" % exc)
        self.output.info("pbseqlib test: exe=%s libdirs=%s" % (exe, libdirs))
        # Best-effort proof of the static-first route: show whether the
        # binary still has DT_NEEDED libblasr.so. Missing readelf on the
        # minimal OHOS rootfs degrades to a warning, never a failure.
        try:
            self.run('readelf -d "%s" 2>&1 | head -n 20' % exe, ignore_errors=True)
        except Exception:
            pass
        if not os.path.isfile(exe):
            import glob as _glob
            tree = []
            try:
                for root, _ds, files in os.walk(self.build_folder):
                    level = root.replace(self.build_folder, "").count(os.sep)
                    if level > 4:
                        _ds[:] = []
                        continue
                    tree.append(root + " : " + ",".join(sorted(files)[:10]))
                    if len(tree) > 30:
                        break
            except Exception:
                pass
            raise ConanException(
                "test_pbseqlib binary missing at %s; tree=%s" % (exe, tree)
            )
        logfile = os.path.join(self.build_folder, "test_package.log")
        ld = ":".join(libdirs)
        # OHOS loader ignores LD_LIBRARY_PATH (HMBS stale_runtime_library
        # diagnosis 2026-10-14: nm proves this package's libblasr.so DOES
        # export DNASequence symbols yet the loader reports them missing,
        # i.e. it loads a stale system lib). Preload THIS package's
        # libblasr.so so its symbols win regardless of search order.
        # LD_LIBRARY_PATH prefix is kept for transitive deps
        # (hdf5/htslib/zlib). Previous round only hardened libdirs/probes;
        # this round changes the loading mechanism itself.
        preload = ""
        _preload_searched = []
        try:
            _dep = self.dependencies["pbseqlib"]
            _search = []
            try:
                for _d in (_dep.cpp_info.libdirs or []):
                    if _d and os.path.isdir(_d) and _d not in _search:
                        _search.append(_d)
            except Exception:
                pass
            try:
                _pkg = _dep.package_folder
                # Exhaustive walk of the whole package folder (not just
                # lib/): the previous round missed when the file lived
                # outside the assumed subdirs, leaving preload empty.
                if _pkg and os.path.isdir(_pkg):
                    for _root, _ds, _files in os.walk(_pkg):
                        if _root not in _search:
                            _search.append(_root)
                        # Bound the walk: package trees are shallow.
                        if _root.replace(_pkg, "").count(os.sep) > 4:
                            _ds[:] = []
            except Exception:
                pass
            _preload_searched = list(_search)
            _cands = []
            for _d in _search:
                try:
                    for _name in os.listdir(_d):
                        if _name == "libblasr.so" or _name.startswith("libblasr.so."):
                            _full = os.path.join(_d, _name)
                            if os.path.isfile(_full):
                                _cands.append(_full)
                except Exception:
                    continue
            _cands.sort(key=lambda p: (os.path.basename(p) != "libblasr.so", len(p)))
            if _cands:
                preload = _cands[0]
        except Exception as exc:
            self.output.warning("pbseqlib test: preload scan skipped (%s)" % exc)
        self.output.info("pbseqlib test: preload=%s" % (preload or "<none>"))
        if not preload:
            # Hard evidence for the next round instead of a silent fallback.
            self.output.warning(
                "pbseqlib test: no libblasr.so* under searched=%s"
                % (_preload_searched[:12],)
            )
        # Explicit LD_LIBRARY_PATH prefix + conanrun env: covers a
        # VirtualRunEnv gap for transitive shared libs (hdf5/htslib/zlib).
        run_cmd = '"%s" > "%s" 2>&1' % (exe, logfile)
        _prefix = []
        if preload:
            _prefix.append('LD_PRELOAD="%s"' % preload)
        if ld:
            _prefix.append('LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"' % ld)
        if _prefix:
            run_cmd = "%s %s" % (" ".join(_prefix), run_cmd)
        self.output.info("pbseqlib test: run_cmd=%s" % run_cmd)
        try:
            self.run(run_cmd, env="conanrun")
        except Exception as exc:
            diag = ""
            try:
                if os.path.isfile(logfile):
                    with open(logfile, encoding="utf-8", errors="replace") as h:
                        diag = h.read()[-2000:]
            except Exception:
                pass
            self.output.warning(
                "pbseqlib test: first launch failed (%s); log tail: %s"
                % (exc, diag[-1200:])
            )
            for probe in (
                'ls -l "%s" 2>&1 | head -n 30' % os.path.dirname(exe),
                'ls -l %s 2>&1 | head -n 40' % " ".join(
                    ['"%s"' % d for d in libdirs[:6]] or ['"."']
                ),
                # The exe only holds UNDEFINED refs; the definitions live in
                # libblasr.so. Probe the package libs (2026-10-14: exe probe
                # always empty, ldd/readelf/file all missing on OHOS).
                # Try PATH nm first, then the compiler-adjacent llvm-nm.
                'for d in %s; do for f in "$d"/libblasr.so* "$d"/libblasr*.so*; do [ -e "$f" ] || continue; echo \"== $f\"; ls -l \"$f\" 2>&1; nm -D --defined-only \"$f\" 2>&1 | grep -E \"DNASequence|TwoBit\" | head -n 8; done; done'
                % " ".join(['"%s"' % d for d in libdirs[:6]] or ['"."']),
                'for d in %s; do for f in "$d"/libblasr.so* "$d"/libblasr*.so*; do [ -e "$f" ] || continue; echo \"== llvm-nm $f\"; llvm-nm -D --defined-only \"$f\" 2>&1 | grep -E \"DNASequence|TwoBit\" | head -n 8; done; done'
                % " ".join(['"%s"' % d for d in libdirs[:6]] or ['"."']),
                'echo \"LD_LIBRARY_PATH=$LD_LIBRARY_PATH\" 2>&1 | head -n 5',
                'echo \"LD_PRELOAD=$LD_PRELOAD\" 2>&1 | head -n 5',
            ):
                try:
                    self.run(probe, ignore_errors=True)
                except Exception:
                    pass
            raise
        with open(logfile, "r", encoding="utf-8", errors="replace") as handle:
            out = handle.read()
        tail = "\n".join(out.splitlines()[-12:])
        self.output.info("test_pbseqlib output tail:\n" + tail)
        # Single deterministic source: the "N/M checks passed" summary line
        # printed by test_pbseqlib itself. No stdout word counting.
        m = re.search(r"(\d+)/(\d+) checks passed", out)
        if not m:
            raise ConanException(
                "test_pbseqlib produced no checks-passed line - harness broken"
            )
        passed = int(m.group(1))
        discovered = int(m.group(2))
        ok = passed == discovered and discovered == 8
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_pbseqlib",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException(
                "test_pbseqlib failed: %d/%d checks passed (expected 8/8)"
                % (passed, discovered)
            )
        # Re-emit the packaged upstream summary (cppdap precedent).
        try:
            dep = self.dependencies["pbseqlib"]
            summary_path = os.path.join(
                dep.package_folder, "res", "upstream_test_result.json"
            )
            with open(summary_path, "r", encoding="utf-8") as handle:
                upstream_marker = json.load(handle)
            for key in (
                "status",
                "framework",
                "command",
                "discovered",
                "executed",
                "passed",
                "failed",
                "skipped",
            ):
                if key not in upstream_marker:
                    raise ConanException(
                        "packaged upstream summary missing key: %s" % key
                    )
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(upstream_marker, ensure_ascii=False)
            )
            print(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(upstream_marker, ensure_ascii=False)
            )
        except ConanException:
            raise
        except Exception as exc:
            self.output.warning(
                "pbseqlib: packaged upstream summary unavailable (%s)" % exc
            )
