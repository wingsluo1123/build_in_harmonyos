#!/usr/bin/env python3
"""Conan recipe for libxtrxdsp 0.0.1-git20230203.271f5e6.

Upstream: myriadrf/libxtrxdsp (formerly xtrx-sdr/libxtrxdsp)
          commit 271f5e60e40dd578c0db5f50ceb7fd6b7119c5ef (2023-02-03,
          "Relicensing the code to Apache 2.0 license.")

DSP support library of the XTRX SDR project: fixed-point/float sample format
conversion (iq8/iq12/iq16 <-> sc32/ic16) and the FIR channel filter used by
libxtrx's transmit/receive paths.

Build system: CMake.  The upstream tree ships a hand-written CMakeLists.txt
(no Autotools / Meson / configure), so a plain CMake build is used.

Two build-time facts drive the HarmonyOS (OHOS) adaptation; both are handled
entirely at recipe level, so **no source patch is required** (R1 parameter
minimisation / R8 "source modification: four don'ts"):

  * `cmake_minimum_required(VERSION 2.8)` in the top-level CMakeLists.txt is
    rejected by CMake >= 4 ("Compatibility with CMake < 3.5 has been
    removed").  `CMAKE_POLICY_VERSION_MINIMUM=3.5` is injected as a **cache**
    variable so it is present before the first `project()` call and re-read
    after `cmake_minimum_required()` (a plain variable would not survive into
    CMakeCache.txt and would not lift the floor).  Same approach as
    archives/a/airspyhf/1.6.8, archives/a/airspy/1.0.10,
    archives/l/laz-perf/3.4.0 and archives/l/libxtrxll/0.0.1-git20201202.1b6eddf.

  * Upstream selects its x86 SIMD translation units only when
    `ARCH MATCHES "^x86.*"`, where ARCH is derived from
    `${CMAKE_C_COMPILER} -dumpmachine`.  On aarch64/OHOS the generic
    implementations in `xtrxdsp_no.c` (+ `xtrxdsp_templates.c`, which that file
    `#include`s) are compiled instead, and `xtrxdsp_config.h` leaves
    XTRXDSP_HAS__SSE2__/__AVX__/__FMA__ undefined because they are guarded by
    `#if defined(__x86_64__) || defined(__i386__)`.  No x86 intrinsics are
    reached on aarch64, so nothing has to be disabled or patched.

E092 (CMAKE_SYSTEM_NAME): CMake ships no "HarmonyOS" platform module.  Conan
maps `os=OHOS` to `CMAKE_SYSTEM_NAME=HarmonyOS`, which CMake reports as
"System is unknown to cmake"; Platform/HarmonyOS.cmake is therefore never
loaded and CMAKE_SHARED_LIBRARY_SONAME_C_FLAG stays unset.  Consequence:
libxtrxdsp.so is linked WITHOUT a DT_SONAME and the upstream
`set_target_properties(... VERSION ... SOVERSION ...)` is ignored (no
libxtrxdsp.so.0 / .so.0.0.1, no symlink chain), which the CI L5a SONAME
quality gate rejects.  Aliasing the system name to Linux restores the full
Unix/Linux platform semantics, which also makes upstream's
`if(CMAKE_SYSTEM_NAME MATCHES "Linux")` branch populate SYSTEM_LIBS for the
`tests/` targets.  Same approach as archives/l/libxtrxll,
archives/a/airspyhf/1.6.8 and archives/a/airspy/1.0.10.

Upstream tests (R51): `tests/` holds two programs, **both of which are run
here from build()**; neither is registered with ctest (no `enable_testing()` /
`add_test()` anywhere in the tree), so ctest reports nothing and the programs
must be driven directly:

  * tests/test_xtrxdsp_sc32i_iq16.c — a self-checking unit test
    (F_VALS=1000 -> 2000 CHECK_I comparisons of the sc32i->iq16 conversion
    against the exact expected values, plus a "Total errors: N" line).  It is
    deterministic and hardware-free, but upstream ends it with a hard-coded
    `return 0;`, so the exit code is not a pass/fail signal: the output is
    captured and the zero-error count is asserted.
  * tests/test_filter.c — the upstream FIR filter pipeline.  It is a
    getopt-driven getopt tool with no assertions, whose documented termination
    for a finite stream is the short-read path (`return 2` after "read %u"; 1
    means the filter failed to initialise, 3 means a short write).  It is
    therefore driven with a deterministic float32 input file and both the
    documented exit status and the sample-count contract
    (out_samples = num_insamples >> decim) are asserted.

Both programs are installed by upstream into <lib>/xtrxdsp and are therefore
NOT advertised through cpp_info.bindirs: this is a library package (R38), so
no commands.json.
"""

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, load, rm)

import math
import os
import struct


def _write_deterministic_stream(path, count):
    """Write `count` float32 samples of a deterministic, finite test signal.

    Used to drive the upstream tests/test_filter pipeline on a machine with no
    hardware: the tool reads fixed-size blocks of float32 samples from -i,
    filters them and writes the filtered stream to -o until a short read ends
    the stream.
    """
    buf = b"".join(struct.pack("<f", math.sin(i * 0.01) * 1000.0)
                   for i in range(count))
    with open(path, "wb") as handle:
        handle.write(buf)


class LibxtrxdspConan(ConanFile):
    name = "libxtrxdsp"
    version = "0.0.1-git20230203.271f5e6"
    description = ("DSP support library of the XTRX SDR project: sample format "
                   "conversion (iq8/iq12/iq16 <-> sc32/ic16) and the FIR "
                   "channel filter used by libxtrx")
    license = "Apache-2.0"
    homepage = "https://github.com/myriadrf/libxtrxdsp"
    url = "https://github.com/myriadrf/libxtrxdsp"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        # Upstream builds `add_library(xtrxdsp SHARED ...)` unconditionally.
        "shared": True,
        # Not a system same-name library (no /lib*/libxtrxdsp.so*), so the
        # shared build is kept (R26 does not apply) and Conan manages the
        # dependency chain.
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        # No patches are needed for this package (see conandata.yml), but the
        # standard export clause is kept so that conandata.yml-declared patches
        # are carried into the build when they are added in the future.
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake 4.x: upstream declares cmake_minimum_required(VERSION 2.8),
        # which is below the removed-compatibility floor.  Must be a *cache*
        # variable so it is set before project() and re-read afterwards.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # E092: no HarmonyOS platform module in CMake -> no SONAME and no
        # Unix/Linux semantics.  Alias the system name to Linux.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # Upstream compiles the x86 SIMD translation units only for
        # ARCH MATCHES "^x86.*"; on aarch64 the generic xtrxdsp_no.c path is
        # used.  PIC is nevertheless forced for any target in the tree so the
        # shared library link is correct regardless of the platform-detection
        # branch that is taken (same rationale as libxtrxll).
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"

        # The .pc file and the CPack block use LIB_SUFFIX; upstream does not
        # define it, keep it empty and explicit (informational only).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["LIB_SUFFIX"] = ""

        tc.generate()

    def build(self):
        apply_conandata_patches(self)  # no-op: this package carries no patches
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 上游官方测试（R51 第二步：实际运行 + 实际断言；两个程序均运行） ──
        # Upstream ships two test programs under tests/; ctest registers none
        # of them (grep -rn "enable_testing|add_test(" -> 0 hits), so both are
        # driven directly here.  Neither can be judged by its exit code alone,
        # hence the explicit assertions below.
        tests_dir = os.path.join(self.build_folder, "tests")

        # 1) tests/test_xtrxdsp_sc32i_iq16 — self-checking unit test
        #    (2000 CHECK_I comparisons).  Upstream ends with a hard-coded
        #    `return 0;` and only accumulates failures in g_errors, so running
        #    it bare would pass even with every comparison failing.  Capture
        #    the output and assert the reported error count.
        unit_log = os.path.join(self.build_folder, "upstream-unit-output.txt")
        unit_exe = os.path.join(tests_dir, "test_xtrxdsp_sc32i_iq16")
        self.run('"%s" > "%s" 2>&1' % (unit_exe, unit_log))
        unit_output = load(self, unit_log)
        self.output.info("upstream test_xtrxdsp_sc32i_iq16: %s"
                         % unit_output.strip())
        if "Total errors: 0" not in unit_output:
            raise ConanException(
                "upstream test_xtrxdsp_sc32i_iq16 reported a non-zero error "
                "count: %s" % unit_output.strip())

        # 2) tests/test_filter — the upstream FIR filter pipeline.  Drive it
        #    with a deterministic stream and assert both the documented
        #    end-of-stream status (2) and the sample-count contract
        #    (out_samples = num_insamples >> decim, decim=0 here).
        blocks = 2
        block_samples = 8192
        filter_in = os.path.join(self.build_folder, "upstream-filter-input.bin")
        filter_out = os.path.join(self.build_folder, "upstream-filter-out.bin")
        filter_log = os.path.join(self.build_folder, "upstream-filter-output.txt")
        _write_deterministic_stream(filter_in, blocks * block_samples)
        filter_exe = os.path.join(tests_dir, "test_filter")
        # rc=2 is the documented end-of-stream status (short read); 1 = filter
        # init failure, 3 = short write.  The final `test` makes self.run()
        # fail the build when the status is anything else.
        self.run('"%s" -i "%s" -o "%s" -m 0 -b %d -d 0 -I 0 > "%s" 2>&1; '
                 'rc=$?; echo "test_filter end-of-stream status: $rc" >> "%s"; '
                 'test "$rc" -eq 2'
                 % (filter_exe, filter_in, filter_out, block_samples,
                    filter_log, filter_log))
        filter_log_text = load(self, filter_log)
        self.output.info("upstream test_filter: %s" % filter_log_text.strip())
        expected_bytes = blocks * block_samples * 4
        actual_bytes = os.path.getsize(filter_out)
        self.output.info("upstream test_filter: %d output bytes (expected %d)"
                         % (actual_bytes, expected_bytes))
        if actual_bytes != expected_bytes:
            raise ConanException(
                "upstream test_filter produced %d output bytes, expected %d "
                "(out_samples must follow num_insamples >> decim)"
                % (actual_bytes, expected_bytes))

    def package(self):
        cmake = CMake(self)
        cmake.install()

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream's CMake install exports no .la files; drop any that a future
        # libtool-based build could add (repository-wide hygiene rule).
        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["xtrxdsp"]
        if self.settings.os in ("Linux", "OHOS"):
            # Upstream SYSTEM_LIBS = rt dl pthread for Linux-like targets; on
            # OHOS (musl/bionic) these live in the base C library, so only the
            # math library that the library actually links is declared.
            self.cpp_info.system_libs = ["m"]
        # The upstream test utilities are installed into <lib>/xtrxdsp and are
        # deliberately NOT advertised as package tools: this is a library
        # package (R38), so no bindirs / commands.json.
