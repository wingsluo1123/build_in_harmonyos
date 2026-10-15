#!/usr/bin/env python3
"""test_package for libgweather4/4.4.4 — real consumer round-trip.

Two binaries are built and run against the packaged library:

* ``test_libgweather4``    — the main consumers surface: the location database
                             (Locations.xml + locations-db), nearest-city search
                             by name and by distance, database consistency, and
                             the GWeatherInfo forecast object lifecycle.
* ``test_detect_degraded`` — the single §3.6-degraded API
                             (gweather_location_detect_nearest_city) must still
                             export its symbol and complete its async contract
                             with G_IO_ERROR_NOT_SUPPORTED.

Both need the packaged locations data and compiled gsettings schema at run
time, so the run goes through VirtualRunEnv (``conanrun``) — a plain
``self.run()`` has no LD_LIBRARY_PATH for the transitive shared libs and would
report a bogus failure.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Libgweather4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Public headers of libgweather4 include glib/gio; CMakeDeps generates
        # empty data for transitive deps in conan 2, so require them explicitly.
        # The version must match the one the recipe overrode to (2.84.0.1).
        self.requires("glib/2.84.0.1", options={"shared": True})

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH for the conan package
        # dirs, so the consumer binary must carry its own DT_RPATH.  Without
        # this, configure and link both succeed (the .pc/CMakeDeps data gives
        # every -L) and only the *run* fails:
        #   Error loading shared library libgweather-4.so.0: (needed by ./test_libgweather4)
        #   Error relocating ./test_libgweather4: gweather_location_get_world: symbol not found
        # i.e. one "Error loading" line per dependency that lives in a conan
        # package folder (libgweather-4, libsoup-3.0, libxml2, libjson-glib),
        # while the libs in the system path (/storage/Users/currentUser/usr/local/lib
        # → glib/gobject/gio/gmodule/gthread/intl) resolve fine.  That split is
        # the fingerprint of a ignored LD_LIBRARY_PATH, not of missing symbols:
        # `llvm-readelf --dyn-syms` shows gweather_location_get_world exported.
        #
        # Two flags are both required: lld defaults to DT_RUNPATH, and musl's
        # dynlink only honours the legacy DT_RPATH, so --disable-new-dtags is
        # what makes the -rpath entries take effect.  CMAKE_BUILD_RPATH is
        # useless here because the conan toolchain sets CMAKE_SKIP_RPATH.
        # Same fix as the merged uhttpmock/0.11.0 and pan/0.165 recipes.
        rpaths = []
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None) or ""
            if not _base:
                continue
            for _p in _d.cpp_info.libdirs:
                if not _p:
                    continue
                _p = _p if os.path.isabs(_p) else os.path.join(_base, _p)
                if os.path.isdir(_p) and _p not in rpaths:
                    rpaths.append(_p)
        if rpaths:
            linker_flags = " ".join(
                ["-Wl,--disable-new-dtags"]
                + ["-Wl,-rpath,%s" % p for p in rpaths]
            )
            cmake.configure(variables={"CMAKE_EXE_LINKER_FLAGS": linker_flags})
        else:
            cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        # Fall back through CONFIG_SHELL -> PATH lookup -> known hnp path, so an
        # empty CONFIG_SHELL (some CI unsets it via "") still resolves a shell.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or \
            "/data/service/hnp/bin/bash"
        # Build LD_LIBRARY_PATH explicitly rather than trusting conanrun alone:
        # VirtualRunEnv writes an empty libdirs entry for deps it considers
        # static, and even when populated it can hold relative paths, which the
        # OHOS loader cannot resolve.  Symptom when this is skipped: configure
        # and link both succeed, then the run dies with "Error loading shared
        # library libgweather-4.so.0" and a wall of "Error relocating ...:
        # gweather_location_get_world: symbol not found" (libsoup3/3.6.5-r1 hit
        # the same thing with libpsl).
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
        syslib = "/storage/Users/currentUser/usr/local/lib"
        if syslib not in libdirs:
            libdirs.append(syslib)
        ldpath = os.pathsep.join(libdirs)
        for binary in ("test_libgweather4", "test_detect_degraded"):
            # Keep ${...} inside a plain string literal: in an f-string it is
            # fine, but it must not be split across two literals, or Python
            # concatenates the parts *before* bash ever sees the text and the
            # parameter expansion reaches bash unexpanded ("bad substitution").
            cmd = (
                bash + " -c 'export LD_LIBRARY_PATH=\"" + ldpath
                + "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"; ./" + binary + "'"
            )
            self.run(cmd, env="conanrun")
