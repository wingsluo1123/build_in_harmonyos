#!/usr/bin/env python3
"""Conan test_package — uuu 1.5.243.

Verifies the uuu binary executes without hardware (R34: substantively
runs the tested package binary).

Runs test_uuu.sh (4 real assertions: executable + no-args version banner
+ -h help + -udev rules), then emits the HMBS evidence markers
(discovered=4, passedCount=4).

Upstream: uuu 1.5.243 has no test suite for the deliverable (see
MANIFEST.yml upstream_test_audit); re-emits HMBS_UPSTREAM_TEST_RESULT
status:"no_tests" every round (build() is skipped on cache hit).
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class UuuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS/shadow CI")
            return
        bin_dir = os.path.join(self.dependencies["uuu"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_uuu.sh")
        # OHOS preflight: conan run env (VirtualRunEnv) does not propagate
        # LD_LIBRARY_PATH to the test shell (acsccid/1.1.13 precedent:
        # explicit LD_LIBRARY_PATH for libusb). uuu links shared
        # libusb-1.0/zstd (kept shared to reuse ohpcd binaries; static
        # rebuild fails), so export their lib dirs explicitly, otherwise
        # the loader reports `Error loading shared library
        # libusb-1.0.so.0/libzstd.so.1` + reloc `symbol not found` (rc=127,
        # 2026-10-17 round). Include the full closure harmlessly.
        # 2026-10-17 fix round: self.dependencies[_dep].package_folder can
        # be None for a resolved-but-folderless node in the test context
        # (this round: TypeError at os.path.join line 48), so guard every
        # lookup instead of assuming non-None.
        libdirs = []
        for _dep in ("libusb", "zstd", "openssl", "zlib", "bzip2"):
            try:
                _folder = self.dependencies[_dep].package_folder
            except KeyError:
                continue
            if not _folder:
                self.output.warning(
                    "test_package: dependency '%s' has no package_folder; skipping in LD_LIBRARY_PATH" % _dep)
                continue
            _lib = os.path.join(_folder, "lib")
            if _lib not in libdirs:
                libdirs.append(_lib)
        _base = 'sh "%s" "%s"' % (script, bin_dir)
        if libdirs:
            _ld = ":".join(libdirs)
            _cmd = 'LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" %s' % (_ld, _base)
        else:
            _cmd = _base
        self.run(_cmd)

        # HMBS evidence: test_package executed 4 real assertions
        # (1. uuu executable; 2. no-args banner; 3. -h help; 4. -udev rules)
        actual_cmd = _cmd
        tp_marker = {
            "executed": True,
            "passed": True,
            "command": actual_cmd,
            "discovered": 4,
            "passedCount": 4,
        }
        tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
        print(tp_msg, flush=True)
        self.output.info(tp_msg)

        # HMBS upstream evidence: re-emit no_tests every round
        # (build() may be skipped on cache hit)
        upstream = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Audited nxp-imx/mfgtools tag uuu_1.5.243 source "
                      "(uuu_source-uuu_1.5.243.tar.gz, sha256 "
                      "dee3be0f337c631bf93232f5ea42440f07782ce005c9219a14731d66bbe83658): "
                      "top-level CMakeLists adds only libuuu + uuu with no "
                      "enable_testing / add_test / BUILD_TESTING; the only "
                      "CTest hits are inside bundled third-party submodules "
                      "(tinyxml2, zlib, zstd) which the top build never "
                      "adds; wrapper/tests are pytest for the python "
                      "wrapper, not built by CMake. Therefore status no_tests.",
        }
        up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(up_msg, flush=True)
        self.output.info(up_msg)
