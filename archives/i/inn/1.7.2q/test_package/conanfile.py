#!/usr/bin/env python3
"""Consumer test for inn/1.7.2q.

Builds test_inn.c against the packaged libinn.a and runs it (20 real API
assertions: wildmat / Radix32 / parsedate / INNVersion / GetTimeInfo), then
smoke-runs the packaged convdate binary on a fixed date string. Pass/fail
comes from the real exit codes — no stdout scraping. Emits
HMBS_TEST_PACKAGE_RESULT with the true case counts and re-emits the
HMBS_UPSTREAM_TEST_RESULT recorded by build() (the marker must appear in
every preflight log even when build() is served from cache).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class InnTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep_dir(self, dep, candidates):
        for cand in candidates:
            if os.path.isabs(cand):
                if os.path.isdir(cand):
                    return cand
            else:
                path = os.path.join(dep.package_folder, cand)
                if os.path.isdir(path):
                    return path
        raise ConanException("inn test: no usable dir among %s" % (candidates,))

    def build(self):
        dep = self.dependencies["inn"]
        include = self._dep_dir(dep, dep.cpp_info.includedirs)
        lib = self._dep_dir(dep, dep.cpp_info.libdirs)
        executables = self.conf.get("tools.build:compiler_executables",
                                    default=None, check_type=dict) or {}
        cc_conf = executables.get("c")
        import shutil as _shutil
        def _cc_usable(v):
            if not v:
                return False
            if os.path.isabs(v):
                return os.path.isfile(v) and os.access(v, os.X_OK)
            return _shutil.which(v) is not None
        if _cc_usable(cc_conf):
            cc = cc_conf
        else:
            if cc_conf:
                self.output.warning(
                    "test toolchain: conf c=%r not executable, probing PATH" % (cc_conf,))
            cc = None
            for _cand in ("clang", "clang-15", "cc", "gcc"):
                _found = _shutil.which(_cand)
                if _found:
                    cc = _found
                    break
            if cc is None:
                cc = "cc"
        src = os.path.join(self.recipe_folder, "test_inn.c")
        out = os.path.join(self.build_folder, "test_inn")
        libinn = os.path.join(lib, "libinn.a")
        if not os.path.isfile(libinn):
            raise ConanException("inn test: packaged library missing: %s" % libinn)
        self.run('"%s" "%s" -o "%s" -I"%s" "%s"'
                 % (cc, src, out, include, libinn), cwd=self.build_folder)

    def test(self):
        package_folder = self.dependencies["inn"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        convdate = os.path.join(bin_dir, "convdate")
        if not os.path.isfile(convdate):
            raise ConanException("inn test: packaged binary missing: %s" % convdate)

        if not can_run(self):
            for path in (os.path.join(self.build_folder, "test_inn"), convdate):
                with open(path, "rb") as binary:
                    magic = binary.read(4)
                if magic != b"\x7fELF":
                    raise ConanException("inn test: not an ELF binary: %s" % path)
            self.output.info("cross build: both test binaries exist with ELF magic")
            return

        results = []
        consumer = os.path.join(self.build_folder, "test_inn")
        try:
            self.run('"%s"' % consumer, cwd=self.build_folder)
            results.append(("consumer_libinn_api", True))
        except Exception:
            results.append(("consumer_libinn_api", False))
        # convdate -n prints the epoch of a fixed date string; exit code
        # proves the packaged binary runs and libinn parsedate() works.
        try:
            self.run('"%s" -n "Thu, 01 Jan 1970 00:00:00 GMT"' % convdate,
                     cwd=self.build_folder)
            results.append(("convdate_smoke", True))
        except Exception:
            results.append(("convdate_smoke", False))

        passed = sum(1 for _name, ok in results if ok)
        marker = {"executed": True,
                  "passed": passed == len(results),
                  "command": "./test_inn ; convdate -n \"Thu, 01 Jan 1970 00:00:00 GMT\"",
                  "discovered": len(results),
                  "passedCount": passed}
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(marker), flush=True)
        if passed != len(results):
            failed = [name for name, ok in results if not ok]
            raise ConanException("inn test_package failures: %s" % ", ".join(failed))

        # Re-emit the upstream audit result persisted by build().
        result_file = os.path.join(package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_file):
            raise ConanException(
                "upstream_test_result.json missing in package: %s" % result_file)
        with open(result_file, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=%s"
              % json.dumps(upstream, ensure_ascii=False), flush=True)
