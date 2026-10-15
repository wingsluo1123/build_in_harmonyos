#!/usr/bin/env python3
"""Conan recipe for vish 0.0.20130812 (direct CXX compile, no autotools).

vish is the VISA shell from Simon Richter's LibreVISA project (upstream:
http://www.librevisa.org, GPL-3.0-or-later): a small CLI that opens a
VISA resource (viOpenDefaultRM -> viOpen), sends SCPI-ish commands
(viWrite/viRead), polls SRQ events (viEnableEvent/viWaitOnEvent/viReadSTB)
and prints responses. The 0.0.20130812 tarball ships a generated
`configure` but NO config.guess/config.sub, and the OHOS worker pool has
no autoconf suite at all (verified in librevisa notes: bare `autoreconf`
fails with Error 127; Conan autoconf pulls m4 from source and dies on the
profile-pinned missing /data/service/hnp/bin/bash). So, exactly like the
librevisa 0.0.20130812 recipe, this recipe does not run autotools:

  * the dependency librevisa/0.0.20130812 is already built and published
    to the ohpcd remote (status=built), providing include/visa.h +
    include/visatype.h + lib/libvisa.a + librevisa.pc (cpp_info.libs
    = ["visa"], system_libs = ["pthread"]);
  * vish.cpp only needs visa.h (all vi* symbols it calls exist in the
    librevisa 0.0.20130812 portable core: viOpenDefaultRM, viFindRsrc,
    viFindNext, viOpen, viClose, viWrite, viRead, viEnableEvent,
    viWaitOnEvent, viReadSTB);
  * direct compile is equivalent to what configure would produce on OHOS:
    AC_CHECK_LIB([visa],[viOpen]) + AC_CHECK_HEADER([visa.h]) both resolve
    against the conan librevisa package, and the executable links
    libvisa.a statically (self-contained);
  * profile CFLAGS/CXXFLAGS/LDFLAGS are honoured by expanding them under
    the conanbuild environment (carries --target/--sysroot), so cross
    flags are not lost.

Since vish.cpp uses `PACKAGE " " VERSION` in its --version branch and
direct compilation does not generate config.h (HAVE_CONFIG_H undefined),
the recipe passes -D'PACKAGE="vish"' -D'VERSION="0.0.20130812"' to the
compiler. vish.cpp relies on std::string/getline without an explicit
#include <string>; libc++ pulls it in transitively via <iostream>, so no
patch is needed (verified during adaptation; see notes.md).

Upstream tests: the 0.0.20130812 tarball has NO tests directory and
Makefile.am declares only bin_PROGRAMS=vish + dist_man_MANS (no
check_PROGRAMS/TESTS target), so upstream_test_total = 0 (R51 audited in
test_package/MANIFEST.yml). The OHOS-specific checks live in
test_package: `vish --version` (exit 0 + version string) and `vish --scan`
(exit 0, real VISA path viOpenDefaultRM -> viFindRsrc -> viClose, no
hardware needed).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


def _resolve_shell():
    """Return a usable POSIX shell (existence-first, then PATH).

    True-machine profiles pin CONFIG_SHELL/SHELL to
    /data/service/hnp/bin/bash, which is absent on some runners
    (Error 127). Only env exports are overridden; no flags touched.
    """
    for cand in (
        os.environ.get("CONFIG_SHELL"),
        os.environ.get("SHELL"),
        "/bin/sh",
        "/system/bin/sh",
    ):
        if cand and os.path.isfile(cand):
            return cand
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if found:
            return found
    return "/bin/sh"


def _pinned_executable(conanfile, key):
    """Read tools.build:compiler_executables[key] if present, else None."""
    try:
        exes = conanfile.conf.get("tools.build:compiler_executables")
    except Exception:
        return None
    if isinstance(exes, dict):
        return exes.get(key)
    return None


def _resolve_cxx(conanfile):
    """C++ compiler: pinned path when it exists, else PATH fallback.

    Mirrors the aggregated compiler-fallback pattern (librevisa): existence
    wins, never trust a pinned absolute path blindly.
    """
    pinned = _pinned_executable(conanfile, "cpp")
    if pinned and os.path.isfile(pinned):
        return pinned
    for name in ("c++", "clang++", "g++"):
        found = shutil.which(name)
        if found:
            return found
    if pinned:
        return pinned
    return "c++"


class VishConan(ConanFile):
    name = "vish"
    version = "0.0.20130812"
    description = "VISA shell: 仪器命令行读写工具 (LibreVISA)"
    license = "GPL-3.0-or-later"
    homepage = "https://tracker.debian.org/pkg/vish"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("librevisa/0.0.20130812")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vish is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _fs_env(self):
        """HMDFS workarounds: explicit PWD plus writable TMPDIR, and a
        sanitized SHELL/CONFIG_SHELL (profile-pinned bash may be absent).
        No autotools PATH handling: this recipe needs no autotools."""
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        shell = _resolve_shell()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        return env

    def _compile_flags(self):
        if str(self.settings.build_type) == "Debug":
            return "-O0 -g"
        return "-O2"

    def build(self):
        src = self.source_folder
        cxx = _resolve_cxx(self)
        flags = self._compile_flags()

        dep = self.dependencies["librevisa"]
        inc_dirs = dep.cpp_info.includedirs
        inc = inc_dirs[0] if inc_dirs else os.path.join(
            dep.package_folder, "include")
        # Static lib from the librevisa package (package lib dir).
        libdirs = dep.cpp_info.libdirs
        libdir = libdirs[0] if libdirs else os.path.join(
            dep.package_folder, "lib")
        libvisa = os.path.join(libdir, "libvisa.a")
        if not os.path.isfile(libvisa):
            raise ConanException("librevisa package missing libvisa.a: " + libvisa)

        src_cpp = os.path.join(src, "vish.cpp")
        if not os.path.isfile(src_cpp):
            raise ConanException("upstream source missing: " + src_cpp)

        bindir = os.path.join(self.build_folder, "manual-bin")
        os.makedirs(bindir, exist_ok=True)
        exe = os.path.join(bindir, "vish")

        # Direct CXX compile + static link. $CXXFLAGS/$LDFLAGS are expanded
        # by the shell from the conanbuild environment so profile cross
        # flags (--target/--sysroot) are honoured. PACKAGE/VERSION macros
        # substitute for the config.h that autotools would generate.
        with self._fs_env().vars(self).apply():
            self.run(
                '"%s" $CXXFLAGS %s -I"%s" -D\'PACKAGE="vish"\''
                ' -D\'VERSION="0.0.20130812"\' "%s" "%s" $LDFLAGS'
                ' -pthread -o "%s"'
                % (cxx, flags, inc, src_cpp, libvisa, exe),
                env="conanbuild",
            )
        if not os.path.isfile(exe) or os.path.getsize(exe) == 0:
            raise ConanException("empty executable: " + exe)

    def package(self):
        copy(self, "vish", src=os.path.join(self.build_folder, "manual-bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # CLI tool: no cpp_info libs, but bindirs must be declared (R38).
        self.cpp_info.bindirs = ["bin"]
