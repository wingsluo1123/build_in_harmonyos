#!/usr/bin/env python3
"""Conan recipe for pgagroal 2.1.0 on HarmonyOS (OHOS/aarch64).

pgagroal is a high performance connection pool for PostgreSQL.  The upstream
build produces `libpgagroal.so` together with five command line tools:
pgagroal (daemon), pgagroal-cli, pgagroal-admin, pgagroal-vault and
pgagroal-config.

Upstream build notes
--------------------
* CMake requires zlib, bzip2, zstd, lz4, OpenSSL, a THREAD implementation and a
  `rst2man` binary.  rst2man only renders the manual pages and
  `doc/CMakeLists.txt` already guards every invocation with
  `if (RST2MAN_FOUND)`, so patch 0001 turns the top level FATAL_ERROR into a
  status message when it is missing; everywhere rst2man exists the behaviour is
  byte for byte the upstream one.
* liburing, libatomic and systemd are only probed under
  `if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")`, which is not taken for OHOS, so
  no io_uring/systemd support is expected nor required on this platform.
* `pgagroal_require_shared_libs()` refuses any dependency that only ships a
  static library.  The zlib, bzip2, lz4 and OpenSSL packages of the OpenHarmony
  registry are position independent static builds, so patch 0002 adds the
  opt-in PGAGROAL_ALLOW_STATIC_DEPS switch; the upstream default (strictly
  shared) is preserved for every other consumer.
* With Clang the project enables LLVM coverage instrumentation on every target
  (`-fprofile-instr-generate -fcoverage-mapping -O0`).  The OHOS SDK ships the
  matching `libclang_rt.profile.a`, so it links and runs; it is left untouched
  on purpose to stay close to upstream.
"""

import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PgagroalConan(ConanFile):
    name = "pgagroal"
    version = "2.1.0"
    description = "High performance connection pool for PostgreSQL"
    license = "BSD-3-Clause"
    homepage = "https://pgagroal.github.io/pgagroal/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Upstream hardcodes `add_library(pgagroal SHARED ${SOURCES})`, so the
    # package is always a shared library and no `shared` option is declared.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8.2")
        self.requires("lz4/1.10.0.3")
        self.requires("openssl/3.5.8.1")
        self.requires("zlib/1.3.2.1")
        self.requires("zstd/1.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    #
    # Dependency location helpers
    #
    @staticmethod
    def _dep_include_dir(dep):
        for inc in dep.cpp_info.includedirs:
            if not os.path.isabs(inc):
                inc = os.path.join(dep.package_folder, inc)
            if os.path.isdir(inc):
                return inc
        return ""

    @staticmethod
    def _dep_library(dep, lib_base):
        for libdir in dep.cpp_info.libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(dep.package_folder, libdir)
            if not os.path.isdir(libdir):
                continue
            # Prefer a shared object when the package provides one, and fall
            # back to the static archive otherwise (see patch 0002).
            for pattern in (f"lib{lib_base}.so*", f"lib{lib_base}.a"):
                matches = sorted(glob.glob(os.path.join(libdir, pattern)))
                if matches:
                    return min(matches, key=len)
        return lib_base

    def _thread_paths(self):
        """Locate pthread.h / libpthread for the target compiler.

        OHOS ships pthread inside the sysroot rather than in the compiler's
        default search path, so both paths are handed to CMake explicitly.
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        include_dir = ""
        library_path = ""
        try:
            output = subprocess.check_output(
                [cc, "-E", "-Wp,-v", "-"],
                stderr=subprocess.STDOUT, input=b"", timeout=10,
            ).decode()
            in_search = False
            for line in output.splitlines():
                if "#include <...> search starts here:" in line:
                    in_search = True
                    continue
                if "End of search list" in line:
                    break
                if in_search:
                    inc = line.strip()
                    if os.path.isfile(os.path.join(inc, "pthread.h")):
                        include_dir = inc
                        break
        except Exception:
            pass
        try:
            for lib_name in ("libpthread.a", "libpthread.so"):
                lib = subprocess.check_output(
                    [cc, "-print-file-name=" + lib_name], timeout=10,
                ).decode().strip()
                if lib and os.path.isfile(lib):
                    library_path = lib
                    break
        except Exception:
            pass
        return include_dir, library_path

    def generate(self):
        tc = CMakeToolchain(self)
        for name, base in (
            ("zlib", "z"),
            ("bzip2", "bz2"),
            ("zstd", "zstd"),
            ("lz4", "lz4"),
        ):
            dep = self.dependencies[name]
            tc.cache_variables[f"{name.upper()}_INCLUDE_DIR"] = self._dep_include_dir(dep)
            tc.cache_variables[f"{name.upper()}_LIBRARY"] = self._dep_library(dep, base)
        # CMake's own FindBZip2/ZLIB modules consume <NAME>_LIBRARIES for
        # bzip2 and <NAME>_LIBRARY for zlib; both spellings are provided so the
        # built in modules and the bundled ones agree.
        bzip2 = self.dependencies["bzip2"]
        tc.cache_variables["BZIP2_LIBRARIES"] = self._dep_library(bzip2, "bz2")
        zlib = self.dependencies["zlib"]
        tc.cache_variables["ZLIB_LIBRARY"] = self._dep_library(zlib, "z")

        openssl = self.dependencies["openssl"]
        openssl_include = self._dep_include_dir(openssl)
        # src/CMakeLists.txt consumes OPENSSL_INCLUDE_DIRS in the non
        # Linux/Darwin branch, but CMake 4.x' FindOpenSSL only defines the
        # singular OPENSSL_INCLUDE_DIR, so the plural is supplied here.
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl_include
        tc.cache_variables["OPENSSL_INCLUDE_DIRS"] = openssl_include
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = self._dep_library(openssl, "ssl")
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = self._dep_library(openssl, "crypto")

        thread_inc, thread_lib = self._thread_paths()
        if thread_inc:
            tc.cache_variables["THREAD_INCLUDE_DIR"] = thread_inc
        tc.cache_variables["THREAD_LIBRARY"] = thread_lib or "pthread"

        # The manual pages need pandoc/pdflatex which are not part of the OHOS
        # toolchain; the reStructuredText sources are packaged as documentation.
        tc.variables["DOCS"] = False
        tc.cache_variables["PGAGROAL_ALLOW_STATIC_DEPS"] = True
        # OHOS runs on the Linux kernel and its libc provides epoll, eventfd
        # and timerfd, which is exactly what upstream selects through
        # `#if HAVE_LINUX` in src/libpgagroal/ev.c.  Upstream derives that macro
        # from `CMAKE_SYSTEM_NAME STREQUAL "Linux"`, and Conan maps OHOS to
        # CMAKE_SYSTEM_NAME=HarmonyOS, so the value is supplied explicitly -
        # without it ev.c falls back to the BSD kqueue backend (sys/event.h)
        # and fails to compile.
        tc.extra_cflags.append("-DHAVE_LINUX=1")
        # Serial builds on purpose: OHOS CI workers intermittently fail to fork
        # under load ("fork: retry: Resource temporarily unavailable"), a
        # parallel build multiplies that pressure, and CMake's feature probes
        # silently answer "no" when they cannot fork.  This drives both
        # `cmake --build -j1` and `cmake --install --parallel 1`.
        self.conf.define("tools.build:jobs", 1)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src", "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # The public headers include <openssl/ssl.h>, so the dependency
        # components must be declared explicitly: CMakeDeps only walks the
        # requires of declared components, a root level cpp_info.requires is
        # ignored and the consumer would miss the transitive include paths.
        self.cpp_info.set_property("cmake_file_name", "pgagroal")
        self.cpp_info.set_property("pkg_config_name", "pgagroal")
        pgagroal = self.cpp_info.components["pgagroal"]
        pgagroal.set_property("cmake_target_name", "pgagroal::pgagroal")
        pgagroal.libs = ["pgagroal"]
        pgagroal.includedirs = ["include"]
        pgagroal.libdirs = ["lib"]
        pgagroal.bindirs = ["bin"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            pgagroal.system_libs = ["pthread"]
        pgagroal.requires = [
            "bzip2::bzip2", "lz4::lz4", "openssl::openssl",
            "zlib::zlib", "zstd::zstd",
        ]
        # libpgagroal.so links the dependency packages (zstd is shipped as a
        # shared object), so make them resolvable for the test_package run.
        for dep in self.dependencies.host.values():
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", dep.cpp_info.libdirs)
