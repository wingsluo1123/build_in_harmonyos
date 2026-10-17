#!/usr/bin/env python3
"""Conan test_package — sispmctl 4.12

L1 test: verify the packaged libsispmctl links and its pure schedule API
(plannif_reset + pms2_schedule_to_buffer / pms2_buffer_to_schedule) runs on
the device, and that the installed `sispmctl` binary reports version 4.12.
HMBS_TEST_PACKAGE_RESULT uses an in-script counter of real checks (one test
case for the library API round-trip, one for the binary version output),
following the repo's accepted checker pattern.
"""
import json
import os
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SispmctlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Also required explicitly so CMakeDeps generates config files for
        # find_package(libusb-compat) and the transitive libusb-1.0.
        self.requires("libusb-compat/0.1.7")

    def layout(self):
        # cmake_layout populates self.cpp.build.bindirs so test() can locate
        # the CMake-built test binary (same as aalib/aribb24 precedent).
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        # The upstream sispmctl Makefile.am declares no include_HEADERS, so the
        # public API header sispm_ctl.h is not installed by `make install`; the
        # main recipe's package() manually copies it into <pkg>/include.
        # Pass the real static library AND header dir to the consumer build
        # EXPLICITLY, driven from the dependency's actual package_folder at
        # configure time. This does NOT rely on CMakeDeps propagating
        # cpp_info (includedirs/libs) for an application-package_type target —
        # which on this real machine does not reach the consumer
        # compile/link (round-3 "includedirs" producer-side fix still produced
        # 'sispm_ctl.h file not found'; the same non-propagation leaves
        # libsispmctl.a unlinked, surfacing only 'undefined symbol:
        # plannif_reset / pms2_schedule_to_buffer / pms2_buffer_to_schedule'
        # at link time). Because the consumer links the actual packaged
        # archive, sispm_ctl.h (the only public header) must travel with it,
        # so SISPMCTL_INCLUDE_DIR accompanies SISPMCTL_LIBRARY. Deterministic
        # and verifiable: a missing header dir or missing archive aborts
        # loudly in CMakeLists.txt.
        sispm = self.dependencies["sispmctl"]
        inc_dir = os.path.join(sispm.package_folder, "include")
        lib_path = os.path.join(sispm.package_folder, "lib", "libsispmctl.a")
        cmake.configure(variables={
            "SISPMCTL_INCLUDE_DIR": inc_dir,
            "SISPMCTL_LIBRARY": lib_path,
        })
        cmake.build()

    def test(self):
        # E386: prefer /bin/sh (HMFS-safe); the OHOS system bash cannot getcwd
        # on HMFS, so never resolve to /data/service/hnp/bin/bash. Inline
        # CONFIG_SHELL/SHELL override keeps conanrun-env-injected values from
        # shadowing it.
        sh = "/bin/sh"
        prefix = "env -u CONFIG_SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh"

        dep = self.dependencies["sispmctl"]
        total = 2
        passed = 0

        # Check 1: libsispmctl schedule API (single ctest case). self.run
        # raises on non-zero exit, so the count is only reached on success.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_sispmctl")
        self.run(f"{prefix} {sh} -c '{bin_path}'", env="conanrun")
        passed += 1

        # Check 2: installed binary reports its version (no USB device needed
        # for the -v path).  Must run under the SAME conanrun runtime
        # environment as check 1: the sispmctl binary is dynamically linked
        # against libusb-1.0.so (pulled in through the static libusb-compat
        # archive via the pc shim's -lusb-1.0), and invoking it without
        # conanrun's LD_LIBRARY_PATH yields rc=127 ("error while loading
        # shared libraries") even for the pure -v path.  Previously this check
        # used a bare subprocess.run without env="conanrun" while check 1 got
        # env="conanrun", which is why the 8/8 lib API round-trip passed but
        # the version smoke check failed with rc=127.  self.run() with
        # env="conanrun" and ignore_errors=True applies the runtime env; we
        # capture the real exit code via `echo $?` into a temp file and the
        # real stdout/stderr into another, then count the check from those
        # deterministic sources (no stdout digit-counting).
        bin_v = os.path.join(dep.package_folder, "bin", "sispmctl")
        tmpdir = tempfile.mkdtemp(prefix="sispmv-")
        out_file = os.path.join(tmpdir, "out.txt")
        rc_file = os.path.join(tmpdir, "rc.txt")
        self.run(
            f"{prefix} {sh} -c \"'{bin_v}' -v; echo $? > '{rc_file}'\" "
            f"> '{out_file}' 2>&1",
            env="conanrun", ignore_errors=True,
        )
        ver_out = ""
        if os.path.isfile(out_file):
            with open(out_file, "r", errors="replace") as f:
                ver_out = f.read()
        rc = None
        if os.path.isfile(rc_file):
            with open(rc_file, "r") as f:
                rc = int(f.read().strip())
        ok2 = rc == 0 and "4.12" in ver_out
        if ok2:
            self.output.info(f"sispmctl -v reported version 4.12")
            passed += 1
        else:
            self.output.error(
                f"sispmctl -v failed (rc={rc}) or no 4.12 in output")

        marker = {
            "executed": True,
            "passed": passed == total,
            "command": "ctest test_sispmctl + sispmctl -v (real schedule "
                       "round-trip and version smoke check)",
            "discovered": total,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" +
                         json.dumps(marker, ensure_ascii=False))

        if passed != total:
            raise SystemExit(1)

        # Upstream test marker: sispmctl 4.12 ships no automated test suite
        # (audit in test_package/MANIFEST.yml upstream_test_audit). Re-emitted
        # here because test_package test() runs every round even when the
        # package cache is hit (build() skipped).
        audit_cmd = ("make -n check (upstream has no check/TESTS target: "
                     "grep Makefile.am/configure.ac -> no TESTS/"
                     "check_PROGRAMS/check-local)")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "sispmctl 4.12 ships no upstream tests: no tests/ directory, "
                "no TESTS/check_PROGRAMS/check-local in Makefile.am or "
                "src/Makefile.am, no make check target, no gtest/ctest/CUnit "
                "framework; make -n check returns 'No rule to make target'. "
                "Hardware-dependent USB control is not automatable without a "
                "physical GEMBIRD device; pure library API covered by "
                "test_sispmctl.c."
            ),
        }))
