#!/usr/bin/env python3
"""Conan recipe — myMPD 25.3.0 (OpenHarmony PC / OHOS aarch64 adaptation).

myMPD (upstream: https://github.com/jcorporation/myMPD) is a standalone web
server that fronts an MPD daemon: the web UI assets are embedded in the
binary, the JSON-RPC API is served over HTTP/WebSocket, and the HTTPS
certificates are generated with OpenSSL on the first start.

The upstream build system is CMake (>= 3.13, project VERSION 25.3.0) with
strict warning flags probed one by one through check_c_compiler_flag.
Adaptation notes:

* Required dependencies come from the artifact registry: pcre2, openssl,
  utf8proc, libid3tag, flac and lua.  libmpdclient is not required: the
  registry publishes no version >= 2.26.0 (the upstream minimum), so the
  vendored dist/libmpdclient (2.26.0) is selected through upstream's own
  "libmpdclient not found" fallback (the option is left at its default:
  upstream's direct ON branch forgets the compile definition that the
  fallback sets, which breaks unit_test and cli_tools/mympd-script).
* myMPD consumes every dependency through find_package in variable style
  (PCRE2_LIBRARIES, OPENSSL_VERSION, LUA_FOUND, ...) with a capitalisation
  that the default CMakeDeps config-file packages do not provide (their
  variable prefixes follow the lowercase conan package name).  CMakeDeps is
  switched to module mode with the upstream-exact cmake_file_name per
  dependency (plus the all-caps OPENSSL/LUA prefix for openssl and lua); the
  generated Find modules deliver the complete legacy variable contract under
  both possible values of CMAKE_FIND_PACKAGE_PREFER_CONFIG.
* MYMPD_EMBEDDED_ASSETS (default ON for non-Debug) runs build.sh
  createassets at configure time; it needs jq, perl and luac (from the
  registry, as tool_requires) plus a gzip command.  The registry publishes no
  gzip package, so the gzip-compatible pigz (official drop-in replacement,
  behaviour selected from argv[0]) provides it: build() derives a gzip-named
  copy below the build folder and generate() prepends its directory to the
  build environment PATH.
* MYMPD_DOC_HTML is left at its upstream default OFF: the html doc step
  runs sphinx/sphinx-lint in a venv with network access, while the man pages
  installed by MYMPD_DOC/MYMPD_MANPAGES need no extra tooling.
* MYMPD_STARTUP_SCRIPT is disabled: upstream would install
  systemd/sysVinit/OpenRC scripts into absolute /usr/lib/systemd/system,
  /etc/init.d and /usr/local/etc/rc.d destinations outside the package.
* CMAKE_INSTALL_PREFIX is pinned to the package folder because upstream
  installs with absolute CMAKE_INSTALL_FULL_* destinations and bakes the
  work/cache/document-root paths into the binary at configure time.
* Patch 0001 routes the unit test scratch directory through TMPDIR (with an
  in-process recursive removal) because /tmp is a read-only mount on
  HarmonyOS PC; with TMPDIR unset the upstream /tmp/mympd-test behaviour is
  kept.  The path building reassigns the sdscatfmt return value: reusing the
  pre-growth sds handle frees the same buffer repeatedly, which the
  platform's hardened jemalloc detects as a fatal assertion (SIGTRAP) while
  the upstream suite runs.
* Patch 0003 invokes build.sh through a bash/sh interpreter located at
  configure time: platforms without binfmt_script cannot execute a script
  file directly.
* Patch 0004 materialises the unit test file directory with a real copy
  (cmake -E rm -r -f + copy_directory) instead of a symlink: symlink
  creation is denied on the platform (EPERM across the filesystem).
* Patch 0005 adds the HarmonyOS CA bundle location (/etc/ssl/certs/cacert.pem)
  to the system certificate store probe list so TLS certificate verification
  finds the platform store.
* Patch 0006 repoints the standalone network test at the gh-proxy.com
  mirror of the same upstream file: the verification network reaches
  gh-proxy.com but not raw.githubusercontent.com.
* Patch 0007 adds the missing all-zero terminator to the getopt_long option
  table: without it, an unmatched or abbreviated long option makes the
  getopt scan read past the array (a deterministic SIGSEGV with the
  platform libc, device-verified).
* Patch 0008 keeps the group-accessible mode of directories created on OHOS
  (guarded by MYMPD_OHOS, which generate() defines for OHOS builds):
  HarmonyOS PC storage resolves access below a directory through its group
  bits and ignores chmod() after creation, so the process umask(0077) set
  in main made every directory unusable below itself; the umask is cleared
  around the mkdir call only and restored immediately after.
* MATH_LIB is pre-seeded to the empty string in the CMake cache: upstream
  runs find_library(MATH_LIB m REQUIRED), but musl keeps the math symbols in
  libc and ships no separate libm to discover.  A set cache variable makes
  find_library skip its search and nothing extra is linked (E376
  target-evidence-bound-empty-library-cache, same treatment as the
  ballerburg/blupimania precedents).
* Upstream probes its hardening flags one by one (check_c_compiler_flag,
  without -Werror) and adds the ones that pass; the x86-only -mshstk and
  -fstack-clash-protection therefore pass the probe here and only turn
  fatal when compiled beside upstream's own -Werror ("argument unused
  during compilation").  On OHOS the C flags carry
  -Werror=unused-command-line-argument, so the probe sees the real -Werror
  semantics and exactly those unsupported flags are excluded, while every
  supported flag is unaffected.
* Upstream adds -D_FORTIFY_SOURCE=2; the OHOS libc's FORTIFY memcpy is a
  static-inline wrapper, which makes clang's -Wstatic-in-inline fire
  inside the vendored mpack C99 inline helpers and turn fatal under
  upstream's -Werror.  -Wno-static-in-inline is added on OHOS (a
  libc-fortify header artifact; the suppression survives the later
  generic -Werror, verified on device).

The upstream unit test suite (a single utest binary, one ctest entry per
test category) is built and executed from build(); the real counts are
reported through the HMBS_UPSTREAM_TEST_RESULT marker.
"""
import json
import os
import shutil
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)

required_conan_version = ">=2.0"


class MympdConan(ConanFile):
    name = "mympd"
    version = "25.3.0"
    description = ("myMPD — standalone web server frontend for the MPD "
                   "music player daemon (OpenHarmony PC)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jcorporation/myMPD"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mympd supports Linux and OHOS targets, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # Required: PCRE2 (search), OpenSSL (TLS + certificates),
        # optional features: utf8proc (utf8 handling), libid3tag (MP3 lyrics
        # tags), flac (FLAC lyrics tags), lua (scripting; the header-only
        # state bridge needs no lua headers in the unit tests).
        self.requires("pcre2/10.48", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/3.5.8.1", transitive_headers=True, transitive_libs=True)
        self.requires("utf8proc/2.11.3.2", transitive_headers=True, transitive_libs=True)
        self.requires("libid3tag/0.16.3", transitive_headers=True, transitive_libs=True)
        self.requires("flac/1.5.0", transitive_headers=True, transitive_libs=True)
        self.requires("lua/5.4.8.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # build.sh createassets runs at configure time (MYMPD_EMBEDDED_ASSETS):
        # the i18n json files are built with jq, the web assets are minified
        # with perl, the lua libraries are syntax-checked with luac (lua ships
        # it in bin/) and the asset archives are written with gzip (derived
        # from pigz, see build()).
        self.tool_requires("jq/1.7.1")
        self.tool_requires("perl/5.42.2.3")
        self.tool_requires("lua/5.4.8.1")
        self.tool_requires("pigz/2.8")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream consumes every dependency through variable-style
        # find_package (PCRE2_LIBRARIES, OPENSSL_VERSION, LUA_FOUND, ...).
        # Ask CMakeDeps for module-mode Find files under the upstream-exact
        # names: the module template emits FOUND/VERSION/VERSION_STRING/
        # INCLUDE_DIR(S)/LIBRARIES for the file_name and for every additional
        # prefix, so both values of CMAKE_FIND_PACKAGE_PREFER_CONFIG resolve
        # to the same complete variable contract.  openssl and lua need the
        # all-caps prefix in addition to the mixed-case file_name because
        # upstream checks OPENSSL_VERSION and LUA_FOUND/LUA_VERSION_STRING.
        # The component and transitive targets stay available either way.
        deps.set_property("pcre2", "cmake_file_name", "PCRE2")
        deps.set_property("pcre2", "cmake_find_mode", "module")
        deps.set_property("openssl", "cmake_file_name", "OpenSSL")
        deps.set_property("openssl", "cmake_additional_variables_prefixes",
                          ["OPENSSL"])
        deps.set_property("openssl", "cmake_find_mode", "module")
        deps.set_property("utf8proc", "cmake_file_name", "UTF8PROC")
        deps.set_property("utf8proc", "cmake_find_mode", "module")
        deps.set_property("libid3tag", "cmake_file_name", "LIBID3TAG")
        deps.set_property("libid3tag", "cmake_find_mode", "module")
        # flac keeps the registry recipe's cmake_file_name (FLAC).
        deps.set_property("flac", "cmake_find_mode", "module")
        deps.set_property("lua", "cmake_file_name", "Lua")
        deps.set_property("lua", "cmake_additional_variables_prefixes", ["LUA"])
        deps.set_property("lua", "cmake_find_mode", "module")
        deps.generate()
        # build.sh createassets performs `check_cmd gzip perl` before any
        # action; gzip has no registry package.  build() derives a gzip-named
        # copy of pigz below the build folder; this build-environment script
        # prepends that directory to PATH.  It is registered for the
        # aggregated conanbuild script, so every command run with
        # env="conanbuild" (cmake.configure(), cmake.build(), the ctest run)
        # sees it.
        shim = os.path.join(self.build_folder, "_toolshim")
        env = Environment()
        env.prepend_path("PATH", shim)
        env.vars(self).save_script("mympd_toolshim")
        toolchain = CMakeToolchain(self)
        # Upstream installs with absolute CMAKE_INSTALL_FULL_* destinations
        # (bindir/man/man8/docdir/localstatedir) and bakes the work/cache/
        # document-root paths into the binary at configure time; pin the
        # prefix to the package folder so every absolute destination lands
        # inside the package.
        toolchain.cache_variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        toolchain.cache_variables["MYMPD_BUILD_TESTING"] = "ON"
        # Libmpdclient: the registry publishes no version >= 2.26.0 (the
        # upstream minimum), so the vendored dist/libmpdclient (2.26.0) is
        # used.  Do NOT set MYMPD_EMBEDDED_LIBMPDCLIENT=ON: that branch in
        # CMakeLists.txt only prints a message and omits the
        # add_compile_definitions("MYMPD_EMBEDDED_LIBMPDCLIENT=ON") call
        # that both other branches perform, so the CMake side would be
        # embedded while the C sources compile as shared: unit_test and
        # cli_tools/mympd-script die on a missing system <mpd/client.h>
        # (fourth device run) and the -v output loses its "(embedded)"
        # marker.  Leaving the option at its upstream default lets
        # find_package(LIBMPDCLIENT) fail here and takes upstream's own
        # "libmpdclient not found" fallback, which sets the option and the
        # compile definition together.
        # Upstream would install init scripts into absolute system paths
        # (/usr/lib/systemd/system, /etc/init.d, /usr/local/etc/rc.d).
        toolchain.cache_variables["MYMPD_STARTUP_SCRIPT"] = "OFF"
        # Upstream probes its hardening flags one by one with
        # check_c_compiler_flag (C_OPTS in CMakeLists.txt) and adds the ones
        # that pass; the probe runs without -Werror, so the x86-only flags
        # -mshstk and -fstack-clash-protection pass the probe on this target
        # and only turn fatal when compiled next to upstream's own -Werror
        # ("argument unused during compilation"; first device run died in
        # dist/libmpdclient objects).  Making the probe see the same -Werror
        # semantics for that one diagnostic group lets exactly those
        # unsupported flags fail their probe and be excluded, while every
        # supported flag is unaffected (E580-class unused-argument
        # diagnostic, liboprf-style outcome: the flag is simply not passed).
        if self.settings.os == "OHOS":
            toolchain.extra_cflags.append("-Werror=unused-command-line-argument")
            # Upstream adds -D_FORTIFY_SOURCE=2 when no sanitizer is active;
            # the OHOS libc exposes the FORTIFY memcpy as a static-inline
            # helper, so clang's -Wstatic-in-inline fires inside mpack.h's
            # C99 inline helpers ("static function 'memcpy' is used in an
            # inline function with external linkage") and becomes fatal
            # under upstream's -Werror (third device run died in
            # dist/mpack/mpack.c).  The diagnostic is a libc-fortify header
            # artifact no source change can satisfy; device probe matrix:
            # it fires exactly when -D_FORTIFY_SOURCE=2 is present, and
            # -Wno-static-in-inline stays effective even with the later
            # generic -Werror on the command line.
            toolchain.extra_cflags.append("-Wno-static-in-inline")
            # Patch 0008 is guarded by MYMPD_OHOS: HarmonyOS PC storage
            # resolves access below a directory through the directory's
            # group bits and ignores later chmod() calls, so testdir() must
            # keep the group-accessible mode of freshly created directories.
            toolchain.extra_cflags.append("-DMYMPD_OHOS")
        # Upstream runs find_library(MATH_LIB m REQUIRED) (CMakeLists.txt);
        # musl keeps the math symbols in libc and ships no separate libm to
        # discover, so the find fails.  A set cache variable (empty string)
        # makes find_library skip its search and links nothing extra (E376
        # target-evidence-bound-empty-library-cache; same treatment as
        # ballerburg/1.2.3-git20250916 and blupimania/1.6.3).
        toolchain.cache_variables["MATH_LIB"] = ""
        # build.sh runs through a shell interpreter (patch 0003).  Prefer an
        # explicitly known one (CONFIG_SHELL, then PATH, then the on-device
        # environment bash location), otherwise leave it to find_program.
        shell = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                 or ("/data/service/hnp/bin/bash"
                     if os.path.exists("/data/service/hnp/bin/bash") else None))
        if shell:
            toolchain.cache_variables["MYMPD_SHELL_EXECUTABLE"] = shell
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        # Derive a gzip-named command from the pigz tool_requires: pigz is
        # the official gzip drop-in replacement (it selects gzip-compatible
        # behaviour from argv[0]) but ships as a pigz-named binary only.  The
        # directory is prepended to the build environment PATH in generate().
        shim = os.path.join(self.build_folder, "_toolshim")
        os.makedirs(shim, exist_ok=True)
        pigz = self.dependencies.build["pigz"]
        pigz_bin = os.path.join(pigz.package_folder,
                                pigz.cpp_info.bindirs[0], "pigz")
        shutil.copy2(pigz_bin, os.path.join(shim, "gzip"))
        os.chmod(os.path.join(shim, "gzip"), 0o755)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    # --------------------------------------------------- upstream test run
    def _run_upstream_tests(self):
        # Upstream registers one ctest entry per test category
        # (`unit_test --filter=<category>.*`): 33 base categories plus
        # lyrics_id3 and lyrics_flac when the optional dependencies are
        # found.  HarmonyOS PC mounts /tmp read-only; patch 0001 routes the
        # test scratch directory through TMPDIR.
        tmpdir = os.path.join(self.build_folder, "_test_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        junit = os.path.join(self.build_folder, "ctest-results.xml")
        if os.path.isfile(junit):
            os.remove(junit)
        command = (f'ctest --test-dir "{self.build_folder}" '
                   f'--output-on-failure --output-junit "{junit}"')
        marker = {
            "status": "failed",
            "framework": "ctest/utest",
            "command": command,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        with env.vars(self).apply():
            rc = self.run(command, env="conanbuild", ignore_errors=True)

        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        if os.path.isfile(junit):
            for suite in ET.parse(junit).getroot().iter("testsuite"):
                for key in counts:
                    counts[key] += int(suite.get(key, 0))
        failed = counts["failures"] + counts["errors"]
        marker.update({
            "discovered": counts["tests"],
            "executed": counts["tests"] - counts["skipped"],
            "passed": counts["tests"] - failed - counts["skipped"],
            "failed": failed,
            "skipped": counts["skipped"],
        })
        status_ok = (rc == 0 and failed == 0 and counts["tests"] > 0)
        marker["status"] = "passed" if status_ok else "failed"
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not status_ok:
            self.output.error(
                "upstream ctest suite failed: rc={}, failed={}, discovered={}".format(
                    rc, failed, counts["tests"]))
            raise ConanException("upstream ctest suite failed")

    # ------------------------------------------------------------- package
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
