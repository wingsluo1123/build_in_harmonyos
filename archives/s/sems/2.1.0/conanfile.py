#!/usr/bin/env python3
"""Conan recipe for sems 2.1.0 -- SIP Express Media Server (C++ SIP media server).

Upstream 2.1.0 dropped the legacy Makefile and is CMake-only.  Its only hard
dependency is libevent (find_package(Libevent2 REQUIRED)); every other
dependency (gsm/speex/openssl/hiredis/mysql++/zrtp/rtmp/libev/...) is probed
without REQUIRED, so it is skipped when the toolchain does not provide it.

Components switched off / excluded so that the OHOS package stays
self-contained:

  * SEMS_USE_PYTHON=OFF      the OHOS sysroot has no Python interpreter
  * SEMS_USE_ILBC=OFF        no codecs (bundled or external iLBC)
  * SEMS_USE_MONITORING=OFF  and the monitoring app module is excluded
                             because its Cargo/Rust tools emit host-arch
                             binaries (or Python wrappers) that make no sense
                             inside an aarch64 OHOS package
  * xmlrpc2di is excluded    its bundled xmlrpc++ unconditionally includes
                             <openssl/crypto.h>; the OHOS sysroot has no
                             OpenSSL and this optional diagnostic module is
                             not referenced by core
  * SEMS_USE_OPUS / SPANDSP / LIBSAMPLERATE / ZRTP / MP3 / G729 / CODEC2 /
    TTS / OPENSSL are OFF upstream by default

The upstream executable links bare `event`/`event_pthreads` names and relies
on the variables filled by cmake/FindLibevent2.cmake, so the recipe presets
those cache variables from the Conan dependency (patch 0002).  Patch 0001
replaces the unconditional pthread_cancel() call with a configure-time
capability probe, needed for libcs that do not provide that symbol (OHOS
musl is one).

Upstream tests: enable_testing() + add_test(NAME Tests COMMAND sems_tests);
core/tests is a fct.h mono-runner with 11 suites / 204 assertions.  The recipe
builds it, ships it as sbin/sems_tests and test_package runs it for real.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SemsConan(ConanFile):
    name = "sems"
    version = "2.1.0"
    description = "SEMS (SIP Express Media Server) - extensible C++ SIP media server"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sems-server/sems"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("sip", "media-server", "voip", "rtp", "sbc")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build/generators"

    def requirements(self):
        self.requires("libevent/2.1.12")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        tc.variables["SEMS_USE_PYTHON"] = "OFF"
        tc.variables["SEMS_USE_ILBC"] = "OFF"
        tc.variables["SEMS_USE_MONITORING"] = "OFF"
        tc.variables["EXCLUDE_APP_MODULES"] = "monitoring xmlrpc2di"

        # Upstream install rules use ${SEMS_*_PREFIX} as absolute prefixes;
        # keep them relative so `cmake --install` lands in the Conan package
        # folder instead of polluting /usr/local on the build machine.
        tc.variables["SEMS_EXEC_PREFIX"] = "."
        tc.variables["SEMS_CFG_PREFIX"] = "."
        tc.variables["SEMS_AUDIO_PREFIX"] = "lib"
        tc.variables["SEMS_DOC_PREFIX"] = "share/doc"

        # Upstream FindLibevent2.cmake fills these via find_path/find_library.
        # Preset them so the cache variables resolve to the Conan dependency;
        # static archives keep the OHOS artifact independent from any libevent
        # shared object present on the target.
        lev = self.dependencies["libevent"]
        components = lev.cpp_info.aggregated_components()
        include_dir = os.path.join(lev.package_folder, components.includedirs[0])
        lib_dir = os.path.join(lev.package_folder, components.libdirs[0])
        tc.variables["LIBEVENT2_INCLUDE_DIR"] = include_dir
        tc.variables["LIBEVENT2_LIB_DIR"] = lib_dir
        libevent_libs = [os.path.join(lib_dir, name)
                         for name in ("libevent.a", "libevent_pthreads.a")]
        tc.variables["LIBEVENT2_LIBRARIES"] = ";".join(
            path for path in libevent_libs if os.path.exists(path))

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream does not install the fct test runner; ship it so consumers
        # (and test_package) can execute the upstream suite for real.
        copy(self, "**/sems_tests", src=self.build_folder,
             dst=os.path.join(self.package_folder, "sbin"), keep_path=False)

        binary = os.path.join(self.package_folder, "sbin", "sems")
        if not os.path.isfile(binary):
            raise ConanException("sems executable missing from package: %s" % binary)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
