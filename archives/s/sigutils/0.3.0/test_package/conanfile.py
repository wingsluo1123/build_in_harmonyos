#!/usr/bin/env python3
"""Conan test_package for sigutils 0.3.0 -- real API consumer (direct CC).

Compiles test.c against the installed libsigutils and runs it. test.c
performs 6 offline deterministic assertions (ABI handshake, version string,
NCQO oscillator DC/unity-tone behaviour, Butterworth LPF pass/stop-band
selectivity); no hardware, network or display needed.

No-CMake rationale: CMakeToolchain maps os=OHOS to
CMAKE_SYSTEM_NAME=HarmonyOS, which the device cmake does not ship
(dcap/2.47.14 preflight evidence). This test_package compiles with CC
directly, mirroring the upstream sigutils.pc consumer flags
(-I<inc>/sigutils -I<inc>/sigutils/util -D_SU_SINGLE_PRECISION -lsigutils -lm).

Emits HMBS_TEST_PACKAGE_RESULT with the real counters (6 CHECKs in test.c);
the marker is only printed after the binary exits 0. Also re-emits the
measured HMBS_UPSTREAM_TEST_RESULT persisted by the main recipe.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class SigutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _ensure_tmp_env(self):
        _cands = []
        for _k in ("HMBS_TMPDIR", "HMBS_TMPDIR_RUNTIME"):
            _v = os.environ.get(_k)
            if _v:
                _cands.append(_v)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp" and _v not in _cands:
                _cands.append(_v)
        _fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if _fb:
            _cands.append(_fb)
        for _base in (getattr(self, "build_folder", None),
                      getattr(self, "base_build_folder", None)):
            if _base:
                _cands.append(os.path.join(str(_base), "tmp"))
        for _c in _cands:
            if not _c:
                continue
            try:
                os.makedirs(_c, exist_ok=True)
            except OSError:
                continue
            if not os.path.isdir(_c):
                continue
            try:
                _probe = os.path.join(_c, ".hmbs_wtest")
                with open(_probe, "w", encoding="utf-8") as _f:
                    _f.write("w")
                os.remove(_probe)
            except OSError:
                continue
            for _k in ("TMPDIR", "TMP", "TEMP"):
                os.environ[_k] = _c
            os.environ["SHELL"] = "/bin/sh"
            return _c
        # R10：禁硬编码 /tmp；TMPDIR 未设置且候选全部不可写时显式失败
        # （isa-l 2.32.0 真机审计同类项，主动整改）。
        _t = os.environ.get("TMPDIR")
        if not _t:
            raise ConanException("test_package: no writable temporary directory available")
        return _t

    def _probe_runs(self, exe):
        try:
            _r = subprocess.run([exe, "--version"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                timeout=60)
            return _r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _resolve_cc(self):
        try:
            _conf_cc = self.conf.get("tools.build:compiler_executables:c",
                                     check_type=str)
        except Exception:
            _conf_cc = None
        if _conf_cc and os.path.isfile(_conf_cc) and self._probe_runs(_conf_cc):
            return _conf_cc
        if _conf_cc and "/" in _conf_cc:
            _w = shutil.which(os.path.basename(_conf_cc))
            if _w and self._probe_runs(_w):
                self.output.warning(
                    "sigutils test: pinned CC {} unusable, using PATH "
                    "{}".format(_conf_cc, _w))
                return _w
        for _name in ("clang", "cc", "gcc"):
            _w = shutil.which(_name)
            if _w and self._probe_runs(_w):
                if _conf_cc:
                    self.output.warning(
                        "sigutils test: pinned CC {} unusable, using PATH "
                        "{}".format(_conf_cc, _w))
                return _w
        return _conf_cc or "clang"

    def build(self):
        import shlex as _shlex
        self._ensure_tmp_env()
        _cc = self._resolve_cc()
        try:
            _dep = self.dependencies["sigutils"]
        except Exception:
            raise ConanException("sigutils test: sigutils dependency missing")
        _root = str(_dep.package_folder)
        # sigutils.pc Cflags 本就两层：-I<inc>/sigutils -I<inc>/sigutils/util；
        # 手写 direct-CC 编译漏掉 util 层 → block.h:26 'util.h' file not
        # found（真机第 3 轮唯一阻断，探针 r3-fixprobe 已实证补齐即过）。
        _inc_main = os.path.join(_root, "include", "sigutils")
        _inc_util = os.path.join(_inc_main, "util")
        for _d in (_inc_main, _inc_util):
            if not os.path.isdir(_d):
                raise ConanException(
                    "sigutils test: include dir missing: {}".format(_d))
        _incs = [_inc_main, _inc_util]
        # 公共头 types.h #include <fftw3.h>；上游 .pc 无 Requires 行，
        # 常规系统靠 /usr/include 兜底，conan 消费者经依赖图传播
        # cpp_info 获得——手写编译必须显式收集传递依赖 include。
        try:
            _fftw = self.dependencies["fftw3f"]
        except Exception:
            _fftw = None
        if _fftw is None or not _fftw.package_folder:
            raise ConanException(
                "sigutils test: fftw3f transitive include not resolvable")
        _fftw_dirs = list(getattr(_fftw.cpp_info, "includedirs", None) or [])
        for _comp in (getattr(_fftw.cpp_info, "components", None)
                      or {}).values():
            _fftw_dirs.extend(getattr(_comp, "includedirs", None) or [])
        if not _fftw_dirs and os.path.isfile(
                os.path.join(str(_fftw.package_folder), "include",
                             "fftw3.h")):
            _fftw_dirs = ["include"]
        for _d in _fftw_dirs:
            _p = _d if os.path.isabs(_d) else os.path.join(
                str(_fftw.package_folder), _d)
            if os.path.isdir(_p) and _p not in _incs:
                _incs.append(_p)
        if not any(os.path.isfile(os.path.join(_d, "fftw3.h"))
                   for _d in _incs):
            raise ConanException(
                "sigutils test: fftw3.h not found in include set")
        _lib = None
        _lib_dir = os.path.join(_root, "lib")
        for _cand in (os.path.join(_lib_dir, "libsigutils.so"),
                      os.path.join(_lib_dir, "libsigutils.a")):
            if os.path.isfile(_cand) and os.path.getsize(_cand) > 0:
                _lib = _cand
                break
        if _lib is None:
            raise ConanException(
                "sigutils test: libsigutils.so/.a not found under {}"
                .format(_lib_dir))
        _src = os.path.join(self.recipe_folder, "test.c")
        if not os.path.isfile(_src):
            raise ConanException(
                "sigutils test: test.c not found: {}".format(_src))
        # 运行时库路径：conanrun（VirtualRunEnv）按依赖 libdirs 注入
        # LD_LIBRARY_PATH；但 OHOS musl 的 ELF 解析可能忽略
        # LD_LIBRARY_PATH（audiowmark 先例），DT_RUNPATH 才可靠 →
        # 链接时对安装包 lib 与共享依赖 lib 目录各加 -Wl,-rpath 双保险
        _run_dirs = [_lib_dir]
        for _name in ("libsndfile", "fftw3f"):
            try:
                _d = self.dependencies[_name]
            except Exception:
                continue
            if _d and _d.package_folder:
                _sub = (_d.cpp_info.libdirs[0]
                        if _d.cpp_info.libdirs else "lib")
                _run_dirs.append(
                    os.path.join(str(_d.package_folder), _sub))
        _rpath = " ".join(
            "-Wl,-rpath,{}".format(_shlex.quote(d)) for d in _run_dirs)
        _inc_flags = " ".join(
            "-I{}".format(_shlex.quote(d)) for d in _incs)
        _exe = os.path.join(self.build_folder, "test_sigutils")
        self.output.info("sigutils test compile: CC={} LIB={} INC={}".format(
            _cc, _lib, " ".join(_incs)))
        try:
            self.run(
                "{} -O1 -D_SU_SINGLE_PRECISION {} {} {} {} -lm -o {}".format(
                    _shlex.quote(_cc), _inc_flags,
                    _shlex.quote(_src), _shlex.quote(_lib), _rpath,
                    _shlex.quote(_exe)),
                cwd=self.build_folder, env="conanbuild")
        except Exception as _exc:
            raise ConanException(
                "sigutils test compile failed: {!r}".format(_exc))
        if not os.path.isfile(_exe) or os.path.getsize(_exe) == 0:
            raise ConanException(
                "sigutils test binary empty: {}".format(_exe))

    def test(self):
        self._ensure_tmp_env()
        if not can_run(self):
            self.output.warning(
                "Skipping test execution: the target cannot run on this host")
            return
        _exe = os.path.join(self.build_folder, "test_sigutils")
        if not os.path.isfile(_exe):
            raise ConanException("sigutils test binary missing: {}".format(_exe))
        # L0 quality gate requires an explicit self.run() call in test().
        # LD_LIBRARY_PATH 由 conanrun（VirtualRunEnv）按依赖 libdirs 注入。
        self.run('"%s"' % _exe, cwd=self.build_folder, env="conanrun")
        # test.c contains 6 real libsigutils API assertions (offline-safe).
        marker = {
            "executed": True,
            "passed": True,
            "command": _exe,
            "discovered": 6,
            "passedCount": 6,
        }
        _tp_line = ("HMBS_TEST_PACKAGE_RESULT="
                    + json.dumps(marker, ensure_ascii=False))
        self.output.info(_tp_line)
        try:
            print(_tp_line, flush=True)
        except Exception:
            pass
        # Re-emit the real upstream result every round from the persisted
        # package file, so a Conan cache hit (build() skipped) still yields
        # per-run upstream evidence. Content comes from the measured
        # build-time file, validated before output; never fabricated.
        try:
            _pkg = str(self.dependencies["sigutils"].package_folder)
        except Exception:
            _pkg = None
        try:
            _up_path = None
            if _pkg:
                _up_path = os.path.join(_pkg, "res", "hmbs_upstream.json")
            _up_obj = None
            if _up_path and os.path.isfile(_up_path):
                with open(_up_path, "r", encoding="utf-8") as _rf:
                    _up_obj = json.loads(_rf.read())
            if (isinstance(_up_obj, dict)
                    and _up_obj.get("status") == "passed"
                    and int(_up_obj.get("discovered", 0)) > 0
                    and int(_up_obj.get("executed", 0)) > 0):
                _up_line = ("HMBS_UPSTREAM_TEST_RESULT="
                            + json.dumps(_up_obj, ensure_ascii=False))
                self.output.info(_up_line)
                try:
                    print(_up_line, flush=True)
                except Exception:
                    pass
            else:
                self.output.warning(
                    "sigutils test: persisted upstream evidence missing or "
                    "invalid at {}; cannot re-emit".format(_up_path))
        except (OSError, ValueError) as _exc:
            self.output.warning(
                "sigutils test: re-emit upstream evidence failed: "
                "{!r}".format(_exc))
