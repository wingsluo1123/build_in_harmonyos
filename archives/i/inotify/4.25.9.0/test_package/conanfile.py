#!/usr/bin/env python3
"""Conan test_package — inotify 4.25.9.0 consumer test.

Builds test_inotify.cpp against the packaged libinotifytools (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
deterministic "CHECK-OK:" lines it writes to a result file for the
HMBS_TEST_PACKAGE_RESULT marker. A second case drives the packaged
inotifywait binary against a scratch directory (create event) and counts
via its exit code. Both counts are deterministic single sources; no
stdout keyword arithmetic or pass-through fallback exists.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# test_inotify.cpp performs exactly 6 CHECKs; the inotifywait functional
# drive below adds 1 more case.
CONSUMER_CHECKS = 6
FUNCTIONAL_CASES = 1
TOTAL_CASES = CONSUMER_CHECKS + FUNCTIONAL_CASES


class InotifyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # NOTE: CMakeToolchain is generated explicitly in generate() (not via
    # the generators attribute) so the落盘 toolchain file can be repaired
    # afterwards (stale baked-in compiler path, see below).
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _is_runnable(exe):
        if not exe:
            return False
        path = exe if os.path.isabs(exe) else (shutil.which(exe) or exe)
        if not path or not os.path.isfile(path):
            found = shutil.which(exe)
            if not found:
                return False
            path = found
        if not os.access(path, os.X_OK):
            return False
        try:
            proc = subprocess.run(
                [path, "--version"], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=30)
            return proc.returncode == 0
        except Exception:
            return False

    def _resolve_compiler(self, kind):
        # Priority: conf tools.build:compiler_executables (if runnable) >
        # CC/CXX env > well-known names on PATH. Mirrors the main recipe's
        # _resolve_tools so both agree on one runnable compiler.
        compilers = {}
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
        except Exception:
            pass
        if kind == "c":
            cands = [compilers.get("c"), os.environ.get("CC"),
                     "clang", "gcc", "cc"]
        elif kind == "cpp":
            cands = [compilers.get("cpp"), os.environ.get("CXX"),
                     "clang++", "g++", "c++"]
        else:
            cands = [compilers.get("archive"), os.environ.get("AR"),
                     "llvm-ar", "ar"]
        for cand in cands:
            if not cand:
                continue
            if os.path.isabs(cand):
                if self._is_runnable(cand):
                    return cand
                continue
            found = shutil.which(cand)
            if found and self._is_runnable(found):
                return found
        return None

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.generate()
        # Experience-1 repair (libnl3 pattern): CMakeToolchain bakes the
        # tools.build:compiler_executables absolute paths into
        # conan_toolchain.cmake. On the真机 /data/service/hnp/bin/clang++
        # is stale (verified by this round's CMake error), so after落盘
        # rewrite any non-runnable compiler path to a trial-run-verified
        # one and export CC/CXX as double insurance.
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cpp")
        if cc:
            os.environ["CC"] = cc
        if cxx:
            os.environ["CXX"] = cxx
        self.output.info("test_package resolved compilers: CC=%s CXX=%s" % (cc, cxx))
        stale = set()
        try:
            conf_compilers = self.conf.get("tools.build:compiler_executables",
                                          default={}, check_type=dict) or {}
            for v in conf_compilers.values():
                if v and os.path.isabs(v) and not self._is_runnable(v):
                    stale.add(v)
        except Exception as exc:
            self.output.warning("test_package conf probe failed: %s" % exc)
        stale.add("/data/service/hnp/bin/clang++")
        stale.add("/data/service/hnp/bin/clang")
        fixed = 0
        for root, _, files in os.walk(self.build_folder):
            for fn in files:
                if fn != "conan_toolchain.cmake":
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                except Exception as exc:
                    self.output.warning("cannot read %s: %s" % (path, exc))
                    continue
                orig = text
                if cxx:
                    for s in stale:
                        if "++" in os.path.basename(s) and s in text:
                            text = text.replace(s, cxx)
                if cc:
                    for s in stale:
                        if "++" not in os.path.basename(s) and s in text:
                            text = text.replace(s, cc)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(text)
                    fixed += 1
                    self.output.info("repaired stale compiler path in %s" % path)
        if not fixed:
            self.output.info("no stale compiler path found in toolchain files")

    def _ensure_writable_tmp(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        tmp = self._ensure_writable_tmp()
        result_file = os.path.join(tmp, "inotify-consumer-result.txt")
        try:
            os.remove(result_file)
        except FileNotFoundError:
            pass
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_inotify")
        os.environ["INOTIFY_TEST_RESULT"] = result_file
        consumer_failed = False
        try:
            self.run("%s \"%s\"" % (bin_path, result_file), env="conanrun")
        except ConanException:
            consumer_failed = True
        ok_count = 0
        if os.path.isfile(result_file):
            with open(result_file, encoding="utf-8", errors="replace") as fh:
                ok_count = fh.read().count("CHECK-OK:")
        # Functional case: packaged inotifywait observes a create event.
        pkg = self.dependencies["inotify"].package_folder
        bindir = self.dependencies["inotify"].cpp_info.bindirs[0]
        inotifywait = os.path.join(pkg, bindir, "inotifywait")
        if not os.path.isfile(inotifywait):
            raise ConanException("inotifywait binary missing at %s" % inotifywait)
        watch_dir = os.path.join(tmp, "inotifywait_test")
        shutil.rmtree(watch_dir, ignore_errors=True)
        os.makedirs(watch_dir, exist_ok=True)
        functional_ok = False
        try:
            self.run(
                "timeout 15 \"%s\" -e create -q \"%s\" & "
                "WATCH_PID=$!; sleep 1; touch \"%s/trigger.txt\"; "
                "wait $WATCH_PID; RET=$?; rm -f \"%s/trigger.txt\"; exit $RET" % (
                    inotifywait, watch_dir, watch_dir, watch_dir),
                env="conanrun")
            functional_ok = True
        except ConanException as exc:
            self.output.warning("inotifywait functional case failed: %s" % exc)
            functional_ok = False
        passed_count = ok_count + (1 if functional_ok else 0)
        all_ok = (ok_count == CONSUMER_CHECKS) and functional_ok and not consumer_failed
        marker = {
            "executed": True,
            "passed": all_ok,
            "command": "%s + inotifywait create-event drive" % bin_path,
            "discovered": TOTAL_CASES,
            "passedCount": passed_count,
        }
        if not all_ok:
            missing = TOTAL_CASES - passed_count
            detail_parts = []
            if ok_count != CONSUMER_CHECKS:
                detail_parts.append("C API consumer %d/%d CHECK-OK" % (ok_count, CONSUMER_CHECKS))
            if not functional_ok:
                detail_parts.append("inotifywait create-event drive failed")
            marker["gaps"] = [{
                "count": missing,
                "category": "ohos_feature",
                "detail": (
                    "consumer/inotifywait cases did not all pass on device: %s; "
                    "inotify depends on the OHOS kernel inotify queue and HMFS "
                    "file visibility" % "; ".join(detail_parts)),
                "evidence": "result file CHECK-OK count=%d + inotifywait exit status above" % ok_count,
            }]
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        self.output.info(line)
        print(line, flush=True)
        if ok_count != CONSUMER_CHECKS or consumer_failed:
            raise ConanException(
                "consumer test failed: CHECK-OK %d/%d" % (ok_count, CONSUMER_CHECKS))
        if not functional_ok:
            raise ConanException("inotifywait functional test failed (create event not observed)")
