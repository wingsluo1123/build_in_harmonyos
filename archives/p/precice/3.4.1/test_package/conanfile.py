#!/usr/bin/env python3
"""Consumer test for precice 3.4.1 — builds test_precice.cpp against the
packaged precice::precice target and runs it.

Emits HMBS_TEST_PACKAGE_RESULT with counts parsed from the single
deterministic source: the test binary stdout line CHECKS_PASSED=x/4.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PreciceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Same OHOS workaround as the main recipe: no Platform/HarmonyOS
        # module ships with CMake, so executable-link TryCompile checks
        # fail on the device toolchain. Static-library try_compile only
        # affects the checks, not the final test executable link.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            # Same SONAME/RPATH gap as the main recipe: without a
            # Platform/HarmonyOS module CMake omits SONAME and RPATH link
            # flags. Needed here so the RUNPATH set in CMakeLists.txt is
            # actually emitted into test_precice (preflight 2026-10-15:
            # "Error loading shared library libprecice.so.3" because the
            # binary carried no RUNPATH and the OHOS loader ignores
            # LD_LIBRARY_PATH). Values only, no platform logic change.
            for _language in ("C", "CXX"):
                tc.variables[
                    "CMAKE_SHARED_LIBRARY_SONAME_%s_FLAG" % _language
                ] = "-Wl,-soname,"
                tc.variables[
                    "CMAKE_SHARED_LIBRARY_RUNTIME_%s_FLAG" % _language
                ] = "-Wl,-rpath,"
                tc.variables[
                    "CMAKE_SHARED_LIBRARY_RUNTIME_%s_FLAG_SEP" % _language
                ] = ":"
                tc.variables[
                    "CMAKE_SHARED_LIBRARY_RPATH_LINK_%s_FLAG" % _language
                ] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
            tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
            tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = True
            # Absolute package lib dirs as explicit -Wl,-rpath: bypasses
            # the RPATH abstraction entirely; deterministic even if the
            # platform module stays silent. Computed from the resolved
            # dependencies (same source as test() lib_dirs below).
            try:
                _rpath_dirs = []
                for _dep in self.dependencies.values():
                    try:
                        _pf = getattr(_dep, "package_folder", None)
                    except Exception:
                        _pf = None
                    if not _pf:
                        continue
                    _ld = os.path.join(_pf, "lib")
                    if os.path.isdir(_ld) and _ld not in _rpath_dirs:
                        _rpath_dirs.append(_ld)
                if _rpath_dirs:
                    _flags = " ".join(
                        "-Wl,-rpath,%s" % _d for _d in _rpath_dirs)
                    # Force DT_RPATH over DT_RUNPATH (6th route): RPATH
                    # propagates to transitive DT_NEEDED while RUNPATH
                    # does not; OHOS ignores LD_LIBRARY_PATH.
                    _flags += " -Wl,--disable-new-dtags"
                    _prev = tc.variables.get("CMAKE_EXE_LINKER_FLAGS", "")
                    tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
                        (_prev + " " + _flags).strip() if _prev else _flags)
                    self.output.info(
                        "test_package RPATH dirs: %s" % (_rpath_dirs,))
            except Exception as _exc:
                self.output.warning(
                    "test_package RPATH probe failed: %s" % (_exc,))
        fixes = {}
        if self.settings.os == "OHOS":
            # The OHOS profile bakes absolute compilers
            # (/data/service/hnp/bin/clang{,++}) that dangle on some
            # preflight clients. Verify usability; only when unusable fall
            # back to the PATH resolution and warn, otherwise zero-change.
            try:
                compilers = self.conf.get(
                    "tools.build:compiler_executables",
                    default={}, check_type=dict) or {}
            except Exception:
                compilers = {}
            for lang, key, tool in (
                    ("C", "c", "clang"), ("CXX", "cpp", "clang++")):
                prof = compilers.get(key, "")
                if prof and os.path.isabs(str(prof)):
                    ok = (os.path.isfile(str(prof))
                          and os.access(str(prof), os.X_OK))
                    if not ok:
                        fb = shutil.which(tool) or ""
                        self.output.warning(
                            "OHOS profile %s compiler '%s' not usable "
                            "(missing or not executable); PATH %s='%s'" % (
                                lang, prof, tool, fb or "<none>"))
                        if fb:
                            tc.variables["CMAKE_%s_COMPILER" % lang] = fb
                            fixes[str(prof)] = fb
        tc.generate()
        if self.settings.os == "OHOS" and fixes:
            # tc.variables alone does not override the compiler baked into
            # conan_toolchain.cmake from the profile conf (main-package
            # preflight proved CMAKE_CXX_COMPILER stayed dangling). Patch
            # the generated file directly; zero-change when usable.
            self._patch_toolchain_compilers(fixes)

    def _patch_toolchain_compilers(self, fixes):
        """Replace dangling absolute compiler paths in conan_toolchain.cmake."""
        cands = []
        try:
            gf = getattr(self, "generators_folder", "")
            if gf:
                cands.append(gf)
        except Exception:
            pass
        for b in (getattr(self, "build_folder", ""),
                  getattr(self, "base_build_folder", "")):
            if b:
                cands.append(os.path.join(b, "build", "Release",
                                           "generators"))
                cands.append(os.path.join(b, "generators"))
        seen = set()
        for d in cands:
            if not d or d in seen:
                continue
            seen.add(d)
            f = os.path.join(d, "conan_toolchain.cmake")
            if not os.path.isfile(f):
                continue
            try:
                with open(f, "r", encoding="utf-8",
                          errors="replace") as fh:
                    txt = fh.read()
                new = txt
                for old, newc in fixes.items():
                    if old and newc and old in new:
                        new = new.replace(old, newc)
                if new != txt:
                    with open(f, "w", encoding="utf-8",
                              newline="\n") as fh:
                        fh.write(new)
                    self.output.warning(
                        "patched dangling compiler in %s: %s" % (
                            f, fixes))
                else:
                    self.output.warning(
                        "dangling compiler not found in %s; "
                        "leaving toolchain as-is" % f)
            except Exception as exc:
                self.output.warning(
                    "cannot patch %s: %s" % (f, exc))

    def build(self):
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            self._dump_cmake_diagnostics()
            raise
        cmake.build()

    def _dump_cmake_diagnostics(self):
        """Emit compiler usability + CMake error-log tails for preflight."""
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables",
                default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        for key, tool in (("c", "clang"), ("cpp", "clang++")):
            prof = compilers.get(key, "")
            which = shutil.which(tool) or "<none>"
            usable = ""
            if prof and os.path.isabs(str(prof)):
                usable = "isfile=%s x_ok=%s" % (
                    os.path.isfile(str(prof)),
                    os.access(str(prof), os.X_OK))
            self.output.error(
                "cmake-diag compiler %s: profile='%s' %s which='%s'" % (
                    key, prof, usable, which))
        roots = []
        for cand in (getattr(self, "build_folder", ""),
                     getattr(self, "base_build_folder", "")):
            if cand and os.path.isdir(cand) and cand not in roots:
                roots.append(cand)
        found = []
        for root in roots:
            for d, dn, fn in os.walk(root):
                for f in ("CMakeError.log", "CMakeOutput.log"):
                    if f in fn:
                        found.append(os.path.join(d, f))
                if len(found) >= 6:
                    break
        if not found:
            self.output.error(
                "cmake-diag: no CMakeError.log/CMakeOutput.log under %s" % (
                    roots))
        for path in sorted(set(found))[:6]:
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as fh:
                    txt = fh.read()
                self.output.error(
                    "cmake-diag %s tail:\n%s" % (path, txt[-4000:]))
            except Exception as exc:
                self.output.error(
                    "cmake-diag: cannot read %s: %s" % (path, exc))

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return
        test_pkg = {
            "executed": True,
            "passed": False,
            "command": "test_precice",
            "discovered": 4,
            "passedCount": 0,
        }
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_precice" + suffix)
        # Normalize to an absolute path: self.cpp.build.bindirs[0] may be
        # relative (preflight 2026-10-15 staged/$ORIGIN logs showed a bare
        # "./libprecice.so.3", i.e. dirname(executable)=="."), which breaks
        # both the $ORIGIN staging below and the loader diagnostics.
        # normpath additionally collapses the "/./" seen in the 18:53 log
        # (.../build/clang-15-armv8-17-release/./test_precice) so $ORIGIN,
        # staging dir and readelf target all denote one exact path.
        try:
            if not os.path.isabs(executable):
                _abs = os.path.join(self.build_folder, executable)
                if os.path.isfile(_abs):
                    executable = _abs
                else:
                    executable = os.path.abspath(
                        os.path.join(self.build_folder, executable))
            executable = os.path.normpath(executable)
            self.output.info(
                "test_package executable='%s' isfile=%s" % (
                    executable, os.path.isfile(executable)))
        except Exception as _exc:
            self.output.warning(
                "test_package executable abspath probe failed: %s" % (_exc,))
        try:
            if self.settings.os == "OHOS":
                self._sign_executable(executable)
        except Exception as exc:
            self.output.error("test_precice signing failed: {}".format(exc))
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        # Runtime library path: packaged precice/boost/libxml2 shared libs +
        # the SDK libc++_shared.so (located via compiler introspection).
        # Some entries in self.dependencies (build-requires / skipped
        # packages) expose package_folder=None; joining that raises
        # TypeError and aborts test() before any marker is emitted
        # (preflight: line 196). Skip folder-less deps explicitly.
        lib_dirs = []
        for _name, dep in self.dependencies.items():
            try:
                pf = getattr(dep, "package_folder", None)
            except Exception:
                pf = None
            if not pf:
                self.output.warning(
                    "test_package: dependency '%s' has no package_folder; "
                    "skipping lib dir" % (_name,))
                continue
            libdir = os.path.join(pf, "lib")
            if os.path.isdir(libdir):
                lib_dirs.append(libdir)
        if self.settings.os == "OHOS":
            try:
                lib_dirs.append(self._find_libcxx_dir())
            except Exception as exc:
                self.output.warning(
                    "test_package: libc++ dir probe failed: %s" % (exc,))
        run_env = os.environ.copy()
        if lib_dirs:
            run_env["LD_LIBRARY_PATH"] = (
                os.pathsep.join(lib_dirs)
                + os.pathsep + run_env.get("LD_LIBRARY_PATH", ""))
        # OHOS loader ignores LD_LIBRARY_PATH for consumer binaries
        # (preflight 2026-10-15: Error loading shared library
        # libprecice.so.3 + symbol-not-found on getVersionInformation /
        # printConfigReference). Point LD_PRELOAD at this package's freshly
        # built libprecice so the test process loads the current product,
        # not a stale system lib. Scoped to the test command env only.
        _preload = ""
        try:
            _prec = self.dependencies.get("precice")
            _ppf = getattr(_prec, "package_folder", None) if _prec else None
            if _ppf:
                import glob as _glob
                _hits = sorted(_glob.glob(
                    os.path.join(_ppf, "lib", "libprecice.so*")))
                self.output.info(
                    "test_package: libprecice candidates=%s" % (_hits,))
                def _is_elf(_p):
                    try:
                        _rp = os.path.realpath(_p)
                        if not os.path.isfile(_rp):
                            return False
                        with open(_rp, "rb") as _fh:
                            return _fh.read(4) == b"\x7fELF"
                    except Exception:
                        return False
                # Prefer the most-versioned real ELF (e.g. .so.3.4.1 over
                # .so.3 over the unversioned .so symlink/linker script) so
                # the OHOS loader preempts any stale system libprecice.so.3
                # (preflight 2026-10-15: preloading libprecice.so left
                # DT_NEEDED libprecice.so.3 unresolved + symbol-not-found).
                _ranked = sorted(
                    _hits,
                    key=lambda _h: (0 if ".so." in os.path.basename(_h) else 1,
                                    -len(os.path.basename(_h)), _h))
                for _h in _ranked:
                    if _is_elf(_h):
                        _preload = os.path.realpath(_h)
                        break
                if _preload:
                    try:
                        _sz = os.path.getsize(_preload)
                    except Exception:
                        _sz = -1
                    self.output.info(
                        "test_package: LD_PRELOAD='%s' size=%s" % (
                            _preload, _sz))
                else:
                    self.output.warning(
                        "test_package: no ELF libprecice under '%s/lib' "
                        "(hits=%s); LD_PRELOAD unset" % (_ppf, _hits))
            else:
                self.output.warning(
                    "test_package: precice package_folder missing; LD_PRELOAD unset")
        except Exception as _exc:
            self.output.warning(
                "test_package: LD_PRELOAD probe failed: %s" % (_exc,))
        if _preload:
            # 5th route (18:53 preflight still stale with single preload +
            # direct exec): the 4th route wrongly assumed one preloaded
            # libprecice suffices once the dead loader cmd is gone, but the
            # error persists byte-identical (libprecice.so.3 not found +
            # getVersionInformation/printConfigReference symbol-not-found),
            # so the single preload is still silently dropped: its own
            # DT_NEEDED (boost/log_setup/xml2/icu) cannot resolve either
            # once the OHOS loader ignores LD_LIBRARY_PATH. Restore the
            # transitive ELF chain (precice first, then boost/xml2/icu/z
            # real ELFs, dedup by realpath) with DIRECT exec - the chain was
            # previously tried only together with the dead explicit-loader
            # command, whose Permission-denied failure masked whether the
            # chain itself works; chain+direct was never tested. RUNPATH
            # ($ORIGIN + absolute package lib dirs), LD_LIBRARY_PATH and the
            # signed $ORIGIN staging stay in place, so whichever mechanism
            # the device loader honors will resolve. Scoped to the test
            # command env only.
            try:
                _chain = [_preload]
                _seen_pre = {os.path.realpath(_preload)}
                import glob as _glob3
                for _ld in lib_dirs:
                    try:
                        _s_hits = sorted(_glob3.glob(
                            os.path.join(_ld, "*.so*")))
                    except Exception:
                        continue
                    for _s in _s_hits:
                        try:
                            _rp = os.path.realpath(_s)
                            if _rp in _seen_pre or not os.path.isfile(_rp):
                                continue
                            with open(_rp, "rb") as _fh:
                                if _fh.read(4) != b"\x7fELF":
                                    continue
                            _bn = os.path.basename(_s)
                            if not (_bn.startswith("libprecice")
                                    or _bn.startswith("libboost")
                                    or _bn.startswith("libxml2")
                                    or _bn.startswith("libicu")
                                    or _bn.startswith("libz")):
                                continue
                            _chain.append(_rp)
                            _seen_pre.add(_rp)
                        except Exception:
                            continue
                self.output.info(
                    "test_package LD_PRELOAD chain(%d)=%s" % (
                        len(_chain), _chain))
                _prev_pre = run_env.get("LD_PRELOAD", "")
                run_env["LD_PRELOAD"] = os.pathsep.join(_chain) + (
                    os.pathsep + _prev_pre if _prev_pre else "")
            except Exception as _exc:
                self.output.warning(
                    "test_package LD_PRELOAD chain failed: %s" % (_exc,))
            if not run_env.get("LD_PRELOAD", ""):
                try:
                    _prev_pre = run_env.get("LD_PRELOAD", "")
                    run_env["LD_PRELOAD"] = _preload + (
                        os.pathsep + _prev_pre if _prev_pre else "")
                    self.output.info(
                        "test_package LD_PRELOAD fallback single='%s'" % (
                            _preload,))
                except Exception as _exc:
                    self.output.warning(
                        "test_package LD_PRELOAD set failed: %s" % (_exc,))
        # RUNPATH (see generate() + CMakeLists.txt) plus the LD_PRELOAD
        # chain above. Verify it here and stage an $ORIGIN fallback copy
        # next to the binary so DT_NEEDED resolves even if the loader
        # strips env vars. Best-effort diagnostics only; never fail the
        # test on probe errors.
        try:
            _bindir = os.path.dirname(os.path.abspath(executable))
            self.output.info("test_package bindir='%s'" % (_bindir,))
            # readelf via PATH first, then the compiler dir / hnp bin (the
            # signing tools live there; readelf is usually beside them but
            # not on PATH on preflight clients).
            _re_cands = []
            for _tool in ("llvm-readelf", "readelf"):
                _w = shutil.which(_tool) or ""
                if _w:
                    _re_cands.append(_w)
            try:
                _compilers = self.conf.get(
                    "tools.build:compiler_executables",
                    default={}, check_type=dict) or {}
                _cdir = os.path.dirname(_compilers.get("cpp", ""))
                for _tool in ("llvm-readelf", "readelf"):
                    for _p in (os.path.join(_cdir, _tool) if _cdir else "",
                               os.path.join("/data/service/hnp/bin", _tool)):
                        if _p and os.path.isfile(_p) and _p not in _re_cands:
                            _re_cands.append(_p)
            except Exception:
                pass
            for _re in _re_cands:
                if _re and os.path.isfile(executable):
                    try:
                        _rp = subprocess.run(
                            [_re, "-d", executable],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True, timeout=60)
                        # Full dump tail as ground truth (6th route): the
                        # previous PATH|NEEDED grep hid whether RUNPATH or
                        # RPATH is present at all. Next round must decide on
                        # this dump, not on another blind env guess.
                        _dyn = _rp.stdout.splitlines()
                        self.output.info(
                            "test_package dynamic section (%s) last40: %s" % (
                                _re, _dyn[-40:]))
                        _runpath_hits = [
                            ln for ln in _dyn
                            if ("RUNPATH" in ln or "RPATH" in ln)
                            and ("ORIGIN" in ln
                                 or any(_ld in ln for _ld in lib_dirs))]
                        if _runpath_hits:
                            self.output.info(
                                "test_package RPATH ok: %s" % (
                                    _runpath_hits[:4],))
                        else:
                            self.output.warning(
                                "test_package RPATH missing $ORIGIN/package "
                                "dirs; stale system lib likely wins (see "
                                "full dump above)")
                        break
                    except Exception as _exc:
                        self.output.warning(
                            "test_package readelf probe failed: %s" % (_exc,))
            # Stage $ORIGIN fallback: copy the packaged SONAME chains for
            # precice AND its transitive shared deps (boost/libxml2/icu/z)
            # next to test_precice (matches CMakeLists $ORIGIN RPATH).
            # Symlinks (libprecice.so -> .so.3 -> .so.3.4.1) are materialized
            # under their link names so DT_NEEDED libprecice.so.3 resolves.
            # Staged copies are OHOS-signed like the binary itself.
            try:
                if os.path.isdir(_bindir):
                    import glob as _glob2
                    _staged = 0
                    for _ld in lib_dirs:
                        try:
                            _cands = sorted(_glob2.glob(
                                os.path.join(_ld, "*.so*")))
                        except Exception:
                            continue
                        for _src in _cands:
                            _bn = os.path.basename(_src)
                            if not (_bn.startswith("libprecice")
                                    or _bn.startswith("libboost")
                                    or _bn.startswith("libxml2")
                                    or _bn.startswith("libicu")
                                    or _bn.startswith("libz")):
                                continue
                            if not os.path.isfile(_src) \
                                    and not os.path.islink(_src):
                                continue
                            try:
                                with open(os.path.realpath(_src), "rb") as _fh:
                                    if _fh.read(4) != b"\x7fELF":
                                        continue
                            except Exception:
                                continue
                            _dst = os.path.join(_bindir, _bn)
                            try:
                                if os.path.exists(_dst) and os.path.realpath(
                                        _src) == os.path.realpath(_dst):
                                    continue
                            except Exception:
                                pass
                            try:
                                shutil.copy2(os.path.realpath(_src), _dst)
                                _staged += 1
                                self.output.info(
                                    "test_package staged $ORIGIN lib: %s"
                                    % (_dst,))
                                if self.settings.os == "OHOS":
                                    try:
                                        self._sign_executable(_dst)
                                    except Exception as _exc:
                                        self.output.warning(
                                            "test_package staged sign "
                                            "failed for %s: %s" % (
                                                _dst, _exc))
                            except Exception as _exc:
                                self.output.warning(
                                    "test_package stage failed for %s: %s" % (
                                        _src, _exc))
                    self.output.info(
                        "test_package staged %d $ORIGIN libs" % (_staged,))
                    # 7th route (signing axis, never tried): all 6 prior
                    # routes preloaded the UNSIGNED Conan package-cache
                    # libprecice (package_folder/lib). OHOS code-signing
                    # enforcement silently drops unsigned preloads, which
                    # explains byte-identical failure across every search-path
                    # combo while upstream ctest (build tree signed via
                    # _sign_ohos_runtime_tree before ctest) passes 519/519.
                    # The staged $ORIGIN copies above ARE signed. Re-point
                    # both env channels at the SIGNED staged dir: bindir
                    # first on LD_LIBRARY_PATH, and LD_PRELOAD rebuilt from
                    # staged signed ELFs (precice first, then boost/xml2/icu/
                    # z). Scoped to the test command env only.
                    try:
                        _signed = []
                        try:
                            import glob as _glob4
                            _s_cands = sorted(_glob4.glob(
                                os.path.join(_bindir, "*.so*")))
                        except Exception:
                            _s_cands = []
                        for _s in _s_cands:
                            try:
                                if not os.path.isfile(_s):
                                    continue
                                with open(os.path.realpath(_s),
                                          "rb") as _fh:
                                    if _fh.read(4) != b"\x7fELF":
                                        continue
                                _bn4 = os.path.basename(_s)
                                if not (_bn4.startswith("libprecice")
                                        or _bn4.startswith("libboost")
                                        or _bn4.startswith("libxml2")
                                        or _bn4.startswith("libicu")
                                        or _bn4.startswith("libz")):
                                    continue
                                _signed.append(os.path.realpath(_s)
                                               if os.path.realpath(_s)
                                               else _s)
                            except Exception:
                                continue
                        # Precice first so its symbols preempt any stale
                        # system libprecice.so.3.
                        _signed = sorted(
                            _signed,
                            key=lambda _h: (
                                0 if "libprecice" in os.path.basename(_h)
                                else 1, _h))
                        self.output.info(
                            "test_package signed staged libs(%d)=%s" % (
                                len(_signed), _signed))
                        if _signed:
                            _old_ld = run_env.get("LD_LIBRARY_PATH", "")
                            if _bindir not in _old_ld.split(os.pathsep):
                                run_env["LD_LIBRARY_PATH"] = _bindir + (
                                    os.pathsep + _old_ld if _old_ld else "")
                            # 8th route (minimal-preload axis, never tried):
                            # the 7th route preloaded all 25 signed staged
                            # libs (~2700 chars, libprecice 3x duplicated as
                            # .so/.so.3/.so.3.4.1). musl silently drops an
                            # overlong/duplicated LD_PRELOAD as a whole,
                            # which matches the blank-output failure. The 4th
                            # route's single preload pointed at the UNSIGNED
                            # package cache. Preload exactly ONE signed
                            # staged file: the SONAME the binary asks for
                            # (libprecice.so.3). Transitive boost/xml2 stay
                            # resolvable via RPATH + signed $ORIGIN staging
                            # in the same dir; they must NOT be preloaded.
                            _soname_pre = ""
                            for _cand_pre in _signed:
                                if os.path.basename(_cand_pre) == \
                                        "libprecice.so.3":
                                    _soname_pre = _cand_pre
                                    break
                            if not _soname_pre:
                                for _cand_pre in _signed:
                                    if "libprecice" in os.path.basename(
                                            _cand_pre):
                                        _soname_pre = _cand_pre
                                        break
                            if not _soname_pre:
                                _soname_pre = _signed[0]
                            run_env["LD_PRELOAD"] = _soname_pre
                            self.output.info(
                                "test_package env override: LD_LIBRARY_PATH"
                                "='%s' LD_PRELOAD='%s'" % (
                                    run_env["LD_LIBRARY_PATH"],
                                    run_env["LD_PRELOAD"]))
                        else:
                            self.output.warning(
                                "test_package signed staged list empty; "
                                "keeping package-cache LD_PRELOAD")
                    except Exception as _exc:
                        self.output.warning(
                            "test_package signed-env override failed: %s"
                            % (_exc,))
            except Exception as _exc:
                self.output.warning(
                    "test_package $ORIGIN staging failed: %s" % (_exc,))
        except Exception as _exc:
            self.output.warning(
                "test_package RPATH diagnostics failed: %s" % (_exc,))
        # Direct execution only (4th route): the 3rd-cycle explicit musl
        # loader path (`ld-musl-*.so.1 --library-path <dirs> <exe>`)
        # is removed. Preflight 2026-10-15 17:43 proved it fails with
        # `/bin/sh: /lib/ld-musl-aarch64.so.1: Permission denied` while the
        # preflight capability set reports chmod=0, so +x on /lib can never
        # be repaired from the recipe. The binary's own PT_INTERP loads the
        # same loader via the kernel without needing +x on the loader path
        # itself. Library resolution relies on the RUNPATH embedded at link
        # time ($ORIGIN + absolute package lib dirs) plus the signed $ORIGIN
        # staging above and the single-lib LD_PRELOAD fallback. No
        # shell wrapper: exec the absolute binary path directly so the
        # failure mode (loader/library/signature) stays observable.
        cmd = [executable]
        try:
            proc = subprocess.run(
                cmd, cwd=self.build_folder,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=300, env=run_env)
            output = proc.stdout
        except Exception as exc:
            self.output.error("test_precice execution failed: {}".format(exc))
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info(output[-2000:])
        m = re.search(r"CHECKS_PASSED=(\d+)/(\d+)", output)
        if m is not None:
            passed_count, total = int(m.group(1)), int(m.group(2))
            test_pkg["discovered"] = total
            test_pkg["passedCount"] = passed_count
            test_pkg["passed"] = (passed_count == total and total > 0)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        if not test_pkg["passed"]:
            raise RuntimeError("test_precice checks failed")

    def _find_libcxx_dir(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        # The OHOS profile cxx may dangle (/data/service/hnp/bin/clang++
        # missing on some preflight clients, preflight 2026-10-15). Fall back
        # to the PATH resolution before probing -print-file-name.
        if not (cxx and os.path.isfile(str(cxx))
                and os.access(str(cxx), os.X_OK)):
            _fb = shutil.which("clang++") or shutil.which("clang") or ""
            if _fb:
                self.output.warning(
                    "test_package: profile cxx '%s' not usable; using PATH "
                    "'%s' for libc++ probe" % (cxx, _fb))
                cxx = _fb
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "failed to locate libc++_shared.so via {}: {}".format(cxx, exc))
        if not out or out == "libc++_shared.so":
            raise ConanInvalidConfiguration("clang could not locate libc++_shared.so")
        return os.path.dirname(out)

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool")
        temporary = "{}.signing".format(executable)
        try:
            shutil.copy2(executable, temporary)
            self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, temporary))
            self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, temporary, temporary))
            os.replace(temporary, executable)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")
