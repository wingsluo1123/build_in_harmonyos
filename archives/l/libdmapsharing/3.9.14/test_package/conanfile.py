#!/usr/bin/env python3
"""Conan test_package for libdmapsharing 3.9.14 — Conan consumer test.

Builds test_dmapsharing.c with CMake (CMakeDeps + CMakeToolchain) and runs it.
The test exercises real libdmapsharing APIs: dmap_md5_generate known-vector,
dmap_md5_progressive_* streaming round-trip, dmap_utils_mime_to_format, and
GObject type-system registration (catches double-glib "existing type" SIGABRT).

libdmapsharing is STATIC and its public headers include glib/gobject headers
and <libsoup/soup.h>; linking pulls the shared glib/soup/avahi/check runtimes.
conan 2.29 CMakeDeps emits EMPTY data for transitive dependencies (libsoup3-r3
precedent), so headers/lib dirs do NOT reach this consumer through the package's
cpp_info.requires alone. We therefore explicitly require the real direct deps
so CMakeDeps generates complete targets for them, and link them explicitly in
CMakeLists.txt (both the -I for compile and the shared link line for runtime).

Counts come from the binary's own deterministic summary line.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdmapsharingTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # ⚠️ Listing generators explicitly REPLACES the conan defaults, so we must
    # carry VirtualRunEnv/VirtualBuildEnv too: test() uses env="conanrun", which
    # needs a generated conanrun script (libsoup3-r3 test_package precedent).
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libdmapsharing public headers include glib/gobject + <libsoup/soup.h>;
        # the static lib links the shared glib/soup/avahi/check runtimes.
        # conan 2.29 CMakeDeps emits empty data for transitive deps, so
        # explicitly require the real direct deps to get complete CMake targets
        # (libsoup3-r3 test_package precedent). glib version/options match the
        # libdmapsharing graph (single shared glib/2.84.0.1.1, single GObject
        # copy).
        self.requires("glib/2.84.0.1.1", options={"shared": True})
        self.requires("libsoup3/3.6.5-r3")
        self.requires("avahi-glib/0.9_rc5")
        self.requires("check/0.11.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH, so embed RPATH pointing at
        # the (shared) dependency lib dirs in the test binary (libsoup3-r3
        # verified pattern), so it can find libglib-2.0/libsoup-3.0/avahi/check
        # at run time.
        rpaths = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir:
                    continue
                # libdir may already be absolute (a recipe appending a
                # dependency's libdir to its own cpp_info.libdirs); join only
                # relative entries, keep absolute ones as-is.
                p = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(p) and p not in rpaths:
                    rpaths.append(p)
        if rpaths:
            # OHOS musl's dynlink only honors legacy DT_RPATH (not DT_RUNPATH,
            # lld's default), so also pass --disable-new-dtags.
            linker_flags = " ".join(
                ["-Wl,--disable-new-dtags"] + ["-Wl,-rpath,%s" % p for p in rpaths])
            configure_vars = {"CMAKE_EXE_LINKER_FLAGS": linker_flags}
        else:
            configure_vars = {}
        # The static libdmapsharing-4.0.a's avahi mdns publisher
        # (dmap-mdns-publisher-avahi.c) calls _() via <glib/gi18n.h>, which
        # maps gettext to the glib-mangled symbol g_libintl_gettext living in
        # the libintl that ships alongside glib (NOT in libglib-2.0 itself).
        # The main recipe links "-L<glib libdir> -lintl" into its configure
        # LDFLAGS (libgtop-tools precedent), so the library + unit-test links
        # resolve; but those LDFLAGS are NOT propagated to the consumer, so
        # this test_package link of test_dmapsharing against the static archive
        # fails with "undefined symbol: g_libintl_gettext" (hmbs-preflight
        # 2026-09-28). Add the same "-L<glib libdir> -lintl" to the exe link
        # flags. glib is a direct requirement here, so its package folder is
        # reachable directly.
        glib = self.dependencies.get("glib")
        if glib is not None:
            glib_lib = os.path.join(glib.package_folder, "lib")
            if os.path.isdir(glib_lib):
                intl_flag = f"-L{glib_lib} -lintl"
                existing = configure_vars.get("CMAKE_EXE_LINKER_FLAGS", "")
                configure_vars["CMAKE_EXE_LINKER_FLAGS"] = (
                    (existing + " " if existing else "") + intl_flag)
                self.output.info(
                    "test_package: adding glib libintl to exe link flags: "
                    + intl_flag)
        cmake.configure(variables=configure_vars)
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = (os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL") or shutil.which("bash"))
        # Also export LD_LIBRARY_PATH across all dependency libdirs as
        # belt-and-suspenders on top of the embedded RPATH.
        _seen, libdirs = set(), []
        for _r, _d in self.dependencies.items():
            _k = str(getattr(getattr(_r, "ref", _r), "ref", _r))
            if _k in _seen:
                continue
            _seen.add(_k)
            _base = getattr(_d, "package_folder", None) or ""
            for _p in _d.cpp_info.libdirs:
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs:
                    libdirs.append(_p)
        ldpath = os.pathsep.join(libdirs)
        log = os.path.join(self.build_folder, "test-package.log")
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
            f'./test_dmapsharing > {log} 2>&1; rc=$?; cat {log}; exit $rc\'',
            env="conanrun",
            ignore_errors=True,
        )
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        m = re.search(
            r"DMAP_TEST_PACKAGE_RESULT_TOTAL=(\d+) PASSED=(\d+) FAILED=(\d+)", text)
        if not m:
            raise Exception(
                "test binary did not emit DMAP_TEST_PACKAGE_RESULT_TOTAL; log:\n" + text)
        total = int(m.group(1))
        passed = int(m.group(2))
        failed = int(m.group(3))
        result = {
            "executed": total > 0,
            "passed": failed == 0 and total == passed,
            "command": "./test_dmapsharing",
            "discovered": total,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if failed != 0 or passed != total:
            raise Exception(f"test_package failed: {passed} passed, {failed} failed of {total}")
