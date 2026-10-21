#!/usr/bin/env python3
"""Conan recipe — libhttpserver 0.11.1 (autotools, C++)

libhttpserver: C++ wrapper around GNU libmicrohttpd for embedding HTTP
servers into C++ applications.

Adaptation (pc1-42 r01):
  - bootstrap: release tarball ships no configure -> autoreconf -fi
  - cross triplet: --build=x86_64-unknown-linux-gnu --host=aarch64-linux-ohos
  - configure.ac 0001 patch: linux-ohos host_os branch clears AM_LDFLAGS
    (-lstdc++ hardcoded; OHOS toolchain is libc++ - same as freebsd branch)
  - E011/E114: umask 077 -> 022 in generated configure (HMDFS; harmless on CI)
  - AC_CHECK_HEADER(microhttpd.h)/AC_CHECK_LIB(microhttpd, MHD_get_fdset2)
    cannot run test programs in cross mode -> env preseed ac_cv_* + point
    CPPFLAGS/LDFLAGS at the conan libmicrohttpd package.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH (abiword-plugin precedent)."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("automake", "AUTOMAKE"),
                      ("aclocal", "ACLOCAL")):
        path = _which(tool)
        if path:
            os.environ.setdefault(var, path)


def _which(tool):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, tool)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def _drop_umask_077(conanfile, path):
    """E011/E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Rewrite the umask so config.status can create its temp dir. Harmless on
    the CI's plain Linux workers (umask 022 == default)."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace("umask 077", "umask 022")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibhttpserverConan(ConanFile):
    name = "libhttpserver"
    version = "0.11.1"
    description = "C++ library for embedding an HTTP server into applications (wraps libmicrohttpd)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/etr/libhttpserver"
    url = "https://github.com/etr/libhttpserver"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0: libmicrohttpd 1.0.1 published in the registry (>= 0.9.37 required
        # by upstream configure; MHD_VERSION 0x01000100 verified).
        self.requires("libmicrohttpd/1.0.1")

    def build_requirements(self):
        # The release tarball ships no `configure`, so build() runs
        # `autoreconf -fi` to bootstrap (abiword-plugin precedent).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libhttpserver is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly
        # (config.sub supports *-linux-ohos) so configure never runs the
        # config.guess probe (abiword-plugin precedent).
        tc.configure_args.append("--build=x86_64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-linux-ohos")
        # Dependency wiring: upstream uses AC_CHECK_HEADER([microhttpd.h]) +
        # AC_CHECK_LIB([microhttpd], [MHD_get_fdset2]) — both execute test
        # programs, impossible in cross mode. Point CPPFLAGS/LDFLAGS at the
        # conan package and preseed the cache vars via the environment.
        mhd = self.dependencies["libmicrohttpd"]
        inc = mhd.cpp_info.includedirs[0]
        lib = mhd.cpp_info.libdirs[0]
        tc.configure_args.append("CPPFLAGS=-I{}".format(inc))
        tc.configure_args.append("LDFLAGS=-L{}".format(lib))
        tc.configure_args.append("--disable-examples")
        tc.configure_args.append("--disable-doc")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # Bootstrap: release tarball ships no configure.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E011: relax umask in the generated configure (HMDFS; harmless on CI)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        # Cross compile cache preseeds: the AC_CHECK_HEADER/AC_CHECK_LIB probes
        # would try to execute host binaries, which is impossible; env vars
        # feed configure's site cache. libhttpserver configure checks
        # MHD_get_fdset2 (not MHD_start_daemon).
        env_prefix = {
            "ac_cv_header_microhttpd_h": "yes",
            "ac_cv_lib_microhttpd_MHD_get_fdset2": "yes",
        }
        for k, v in env_prefix.items():
            os.environ[k] = v
        autotools = Autotools(self)
        autotools.configure()
        # E074-adjacent: keep -j modest on HMDFS
        autotools.make(args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        # configure.ac 已保留外部 LDFLAGS（0005 补丁），install 阶段无需再注入 -L
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["httpserver"]
