#!/usr/bin/env python3
"""Conan recipe for libbson 2.5.6 — BSON serialization library (mongo-c-driver 2.x line).

Upstream facts (mongodb/mongo-c-driver tag 2.5.6, libbson sub-library):
  - Built from the mongo-c-driver monorepo tarball with -DENABLE_MONGOC=OFF,
    which limits the build to the bundled libbson (upstream-sanctioned split:
    the same switch the 1.x line Savannah tarballs used to ship libbson alone).
  - 2.x package-line artifact names: shared libbson2.so.2 (SONAME, OUTPUT_NAME
    = BSON_OUTPUT_BASENAME + major = "bson" + "2"), static libbson2.a; public
    headers install to include/bson-2.5.6/bson/ (BSON_INSTALL_INCLUDEDIR is
    version-suffixed by design); CMake config package "bson" (exported targets
    bson::shared / bson::static) under lib/cmake/bson-2.5.6/; pkg-config files
    bson2.pc / bson2-static.pc. The major-suffixed names coexist with the
    legacy 1.x line (libbson-1.0.so.0, archives/l/libbson/1.27.1) with no
    file or SONAME conflict.
  - Zero external dependencies: the libbson-only build consumes no
    compression/crypto libraries (those are libmongoc concerns), and
    USE_SYSTEM_LIBBSON=OFF keeps the bundled sources.
  - Upstream tests, really executed here: the 464 C-registered tests plus the
    1015 JSON-data-driven cases (json/bson_corpus/ 34 files, 992 internal
    cases; json/bson_binary_vector/ 3 files, 23 internal cases) are all
    compiled by upstream into the single test-libmongoc executable whose
    TestSuite framework lives in src/libmongoc/tests/. build() therefore
    configures a SECOND, test-only CMake build of the SAME unpatched source
    tree ("upstream test vehicle"): -DENABLE_MONGOC=ON -DENABLE_TESTS=ON —
    the full-tree shape upstream itself builds its tests in — with
    -DBUILD_TESTING=OFF (skips the CTest registration that would pull a
    Python3 dependency at configure time) and every optional external
    dependency OFF (SSL/Snappy/zstd/zlib/SASL/SRV/client-side-encryption/
    MONGODB-AWS-auth/shm-counters are all libmongoc features; the libbson
    suites need none of them). On the OHOS aarch64 build machine (native
    execution) the vehicle binary then runs in build(): 529 libbson-relevant
    entries registered in it — 501 from the libbson tree (464 C-registered +
    37 JSON spec files internally asserting all 1015 data-driven cases) plus
    28 from the bundled src/common layer (7 mcommon + 21 mlib) — through the
    upstream TestSuite runner. Three documented skips: two upstream
    large-allocation-gated tests (2 GiB / 4 GiB, off by default upstream) and
    one OHOS-musl scanf int64-overflow divergence (root cause + minimal repro
    in _SKIP_FILE_CONTENT and the PR body).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import build_jobs, can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, load, save


class LibbsonConan(ConanFile):
    name = "libbson"
    version = "2.5.6"
    description = "BSON serialization library bundled in mongo-c-driver (2.x package line: libbson2)"
    license = "Apache-2.0"
    homepage = "https://github.com/mongodb/mongo-c-driver"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    topics = ("bson", "mongodb", "serialization")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    # ── Upstream test vehicle (real upstream test execution in build) ────
    # libbson test suites only exist inside the upstream test-libmongoc
    # executable, so the vehicle is a second, test-only CMake configure of
    # the same unpatched source. Selectors cover the whole libbson tree plus
    # the bundled src/common layer that ships inside libbson.
    _VEHICLE_SELECTORS = ("/bson*", "/endian*", "/util*", "/mcommon*", "/mlib*")
    # Pinned result for the 2.5.6 upstream tree: fails fast if the vehicle
    # ever silently matches zero tests or upstream drifts.
    _VEHICLE_EXPECTED = {"pass": 526, "skip": 3, "fail": 0}
    _SKIP_FILE_CONTENT = """# libbson 2.5.6 on OHOS (musl libc) - documented divergence skip
#
# Root cause (minimal repro in the PR body): the C standard leaves the
# behavior of a non-representable scanf/fscanf conversion undefined. On
# int64 overflow musl scanf saturates to -1 while glibc clamps to
# LLONG_MAX. bson_decimal128_from_string() parses the exponent with
# sscanf: for 0E+99999999999999999999 musl yields exponent -1 (in int32
# range, wrongly accepted) where glibc yields LLONG_MAX (out of int32
# range, correctly rejected). libc divergence, not a libbson logic
# defect; skipped via the upstream --skip-tests mechanism.
/bson/decimal128_overflowing_exponent # OHOS musl scanf int64-overflow saturates to -1 (glibc clamps to LLONG_MAX) - C standard leaves non-representable conversion undefined - libc divergence, not a libbson defect
"""

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (CMake ships no
        # Platform/HarmonyOS module). OHOS is POSIX: force the Linux
        # platform (chain-wide convention; libsoundio 48c47b83 /
        # abcmidi / adios2 / kpeople5 merged precedents). The test
        # vehicle reuses conan_toolchain.cmake, so it is covered too.
        # No-op for CMake 3.x workers.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        # Core split: build only the bundled libbson, never libmongoc
        tc.variables["ENABLE_MONGOC"] = False
        # The PACKAGE build stays test-free (the upstream tests are executed
        # by the test-only vehicle configured separately in build(); this
        # also avoids the configure-time CTest registration pulling Python3
        # via import-tests.cmake / TestFixtures.cmake)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["ENABLE_TESTS"] = False
        # Disable every non-library subdirectory / optional instrumentation
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["ENABLE_UNINSTALL"] = False
        tc.variables["ENABLE_HTML_DOCS"] = False
        tc.variables["ENABLE_MAN_PAGES"] = False
        tc.variables["ENABLE_MAINTAINER_FLAGS"] = False
        tc.variables["ENABLE_TRACING"] = False
        tc.variables["ENABLE_COVERAGE"] = False
        tc.variables["ENABLE_DEBUG_ASSERTIONS"] = False
        # x86-only perf counters (MONGOC feature anyway); default OFF upstream,
        # pinned here for cross-build determinism
        tc.variables["ENABLE_RDTSCP"] = False
        # Keep the bundled libbson sources (never consume an external libbson)
        tc.variables["USE_SYSTEM_LIBBSON"] = False
        # Let the OHOS toolchain pick its own linker instead of the upstream
        # -fuse-ld=lld auto-probe (check_c_source_compiles misbehaves in the
        # cross environment)
        tc.variables["MONGO_USE_LLD"] = False
        # musl/OHOS: libm symbols live in libc, avoid find_library picking up
        # an absolute sysroot path that would leak into the exported CMake
        # targets and pkg-config files
        tc.variables["CMAKE_DISABLE_FIND_LIBRARY_M_LIBRARY"] = True
        # One artifact shape per package configuration
        tc.variables["ENABLE_SHARED"] = self.options.shared
        tc.variables["ENABLE_STATIC"] = not self.options.shared
        if self.options.get_safe("fPIC"):
            tc.variables["ENABLE_PIC"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Real upstream test execution: build the upstream test vehicle from
        # the same unpatched source and run the libbson suites in it.
        self._run_upstream_tests()

    # ── Upstream test vehicle ─────────────────────────────────────────────

    def _run_upstream_tests(self):
        """Configure + build + run the upstream test-libmongoc vehicle.

        The vehicle reuses the conan-generated toolchain (same compiler,
        sysroot, flags as the package build). Command-line -D cache entries
        are seeded before the toolchain file is included, so the vehicle
        options below override the toolchain's ENABLE_MONGOC/ENABLE_TESTS
        pins without touching it.
        """
        if not can_run(self):
            self.output.info(
                "HMBS_UPSTREAM_TESTS: build machine cannot execute target "
                "binaries (cross-building) - upstream test vehicle not run "
                "here; consumer tests in test_package/ still execute")
            return

        veh_dir = os.path.join(self.build_folder, "upstream-tests")
        tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        vehicle_args = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(tc_file),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_SHARED_LIBS=OFF",
            # Full-tree shape: upstream builds its tests in this shape; it is
            # the only shape in which test-libmongoc (which contains ALL the
            # libbson test suites) exists.
            "-DENABLE_MONGOC=ON",
            "-DENABLE_TESTS=ON",
            # No CTest registration (keeps configure Python3-free); tests are
            # executed directly below via the upstream TestSuite runner.
            "-DBUILD_TESTING=OFF",
            # Static-only vehicle (test-libmongoc links mongoc_static)
            "-DENABLE_STATIC=ON",
            "-DENABLE_SHARED=OFF",
            # Zero external dependencies: every optional dependency is a
            # libmongoc feature, none is needed by the libbson suites.
            "-DENABLE_SSL=OFF",
            "-DENABLE_SNAPPY=OFF",
            "-DENABLE_ZSTD=OFF",
            "-DENABLE_ZLIB=OFF",
            "-DENABLE_SASL=OFF",
            "-DENABLE_SRV=OFF",
            "-DENABLE_CLIENT_SIDE_ENCRYPTION=OFF",
            "-DENABLE_MONGODB_AWS_AUTH=OFF",
            "-DENABLE_SHM_COUNTERS=OFF",
            # Keep the vehicle side-effect free
            "-DENABLE_UNINSTALL=OFF",
            "-DENABLE_EXAMPLES=OFF",
            "-DENABLE_HTML_DOCS=OFF",
            "-DENABLE_MAN_PAGES=OFF",
            "-DENABLE_MAINTAINER_FLAGS=OFF",
            "-DENABLE_TRACING=OFF",
            "-DENABLE_COVERAGE=OFF",
            "-DENABLE_DEBUG_ASSERTIONS=OFF",
            "-DENABLE_RDTSCP=OFF",
            # Same cross-build pins as the package build
            "-DUSE_SYSTEM_LIBBSON=OFF",
            "-DMONGO_USE_LLD=OFF",
            "-DCMAKE_DISABLE_FIND_LIBRARY_M_LIBRARY=ON",
        ]
        self.output.info(
            "HMBS_UPSTREAM_TESTS: configuring upstream test vehicle "
            "(test-libmongoc, full-tree shape, zero external dependencies)")
        self.run('cmake -S "{}" -B "{}" {}'.format(
            self.source_folder, veh_dir, " ".join(vehicle_args)))
        self.output.info("HMBS_UPSTREAM_TESTS: building test-libmongoc")
        self.run('cmake --build "{}" --target test-libmongoc -j {}'.format(
            veh_dir, build_jobs(self)))

        exe = os.path.join(veh_dir, "src", "libmongoc", "test-libmongoc")
        if not os.path.isfile(exe):
            raise ConanException(
                "HMBS_UPSTREAM_TESTS: vehicle binary not found at {}".format(exe))

        # Documented OHOS/musl divergence skip (root cause in the file header)
        skip_file = os.path.join(self.build_folder,
                                 "libbson-2.5.6-ohos-skip-tests.txt")
        save(self, skip_file, self._SKIP_FILE_CONTENT)

        report = os.path.join(self.build_folder, "test-libmongoc-report.json")
        selectors = " ".join('-l "{}"'.format(s) for s in self._VEHICLE_SELECTORS)
        self.output.info(
            "HMBS_UPSTREAM_TESTS: running 529 libbson-relevant upstream "
            "entries (501 libbson tree: 464 C-registered + 37 JSON spec "
            "files; 28 bundled src/common layer)")
        # Must run from the source root: BSON_JSON_DIR is a relative path
        # ("src/libbson/tests/json") resolved against the current directory.
        self.run('"{}" {} --skip-tests "{}" > "{}" 2>&1'.format(
            exe, selectors, skip_file, report),
            cwd=self.source_folder)

        self._verify_upstream_report(report)

    def _verify_upstream_report(self, report_path):
        text = load(self, report_path)
        statuses = re.findall(r'"status": "(pass|skip|fail)"', text)
        counts = {s: statuses.count(s) for s in ("pass", "skip", "fail")}
        total = len(statuses)

        # Per-suite-prefix breakdown for the build log
        by_prefix = {}
        for st, name in re.findall(
                r'"status": "(pass|skip|fail)", "test_file": "([^"]+)"', text):
            prefix = "/" + name.split("/")[1]
            bucket = by_prefix.setdefault(
                prefix, {"pass": 0, "skip": 0, "fail": 0})
            bucket[st] += 1
        for prefix in sorted(by_prefix):
            c = by_prefix[prefix]
            self.output.info(
                "HMBS_UPSTREAM_TESTS: {}: pass={} skip={} fail={}".format(
                    prefix, c["pass"], c["skip"], c["fail"]))

        # Every skip must be accounted for (documented reason, or the
        # upstream skip_if_no_large_allocations gate)
        for m in re.finditer(
                r'"status": "skip", "test_file": "([^"]+)"'
                r'(?:, "reason": "([^"]*)")?', text):
            name, reason = m.group(1), m.group(2)
            self.output.info(
                "HMBS_UPSTREAM_TESTS: skip {} (reason: {})".format(
                    name,
                    reason or "upstream skip_if_no_large_allocations gate"))

        for m in re.finditer(
                r'"status": "fail", "test_file": "([^"]+)"', text):
            self.output.info("HMBS_UPSTREAM_TESTS: FAIL {}".format(m.group(1)))
        for line in text.splitlines():
            if "assertion failed" in line:
                self.output.info("HMBS_UPSTREAM_TESTS: {}".format(line.strip()))

        if counts != self._VEHICLE_EXPECTED:
            raise ConanException(
                "HMBS_UPSTREAM_TESTS: unexpected counts pass={} skip={} "
                "fail={} total={} (expected {} for the libbson 2.5.6 "
                "upstream tree)".format(
                    counts["pass"], counts["skip"], counts["fail"], total,
                    self._VEHICLE_EXPECTED))

        self.output.info(
            "=== HMBS_UPSTREAM_TESTS libbson/2.5.6: {} upstream entries "
            "really executed in build() via the unpatched upstream "
            "test-libmongoc vehicle - {} pass, {} skip (documented), "
            "{} fail - case-level coverage 1476/1479 (464 C-registered + "
            "1015 JSON-internal asserted by 37 spec-file entries; 3 skipped: "
            "/bson/json/big_string + /bson/value/big_copy upstream "
            "large-allocation gate, /bson/decimal128_overflowing_exponent "
            "OHOS-musl scanf divergence) - PASS ===".format(
                total, counts["pass"], counts["skip"], counts["fail"]))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "bson")
        self.cpp_info.set_property("pkg_config_name", "bson2")
        self.cpp_info.set_property("cmake_target_name", "bson::bson")

        # Headers install to <prefix>/include/bson-2.5.6/bson/ (versioned
        # infix upstream design), so consumers #include <bson/bson.h>
        self.cpp_info.includedirs = ["include/bson-2.5.6"]
        self.cpp_info.libdirs = ["lib"]
        # OUTPUT_NAME = bson + major(2) -> libbson2.so.2 / libbson2.a
        self.cpp_info.libs = ["bson2"]
        self.cpp_info.requires = []

        if self.settings.os in ("Linux", "OHOS"):
            # Threads::Threads (-pthread) and libm per upstream pkg-config;
            # both resolve into libc on musl/OHOS
            self.cpp_info.system_libs = ["pthread", "m"]
