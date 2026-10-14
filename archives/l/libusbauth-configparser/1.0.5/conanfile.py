#!/usr/bin/env python3
"""Conan recipe — libusbauth-configparser 1.0.5 (autotools, OHOS).

libusbauth-configparser is the config-file parser used by the usbauth USB
firewall: a flex/bison lexer+grammar plus a small C API (usbauth_config_read/
write/get_auths/set_auths, parameter/operator string<->enum helpers).

Upstream is a monorepo (kochstefan/usbauth-all) whose top level has no tag;
this recipe pins the v1.0.5 commit (configure.ac AC_INIT says 1.0.5) and
builds only the ``libusbauth-configparser/`` subdirectory (see source()).

OHOS adaptations:
  - the pinned git snapshot ships no ``configure``: build() bootstraps it with
    ``autoreconf -fi`` (automake/libtool come from tool_requires, per the
    libpll/abiword precedent; the autoconf family and flex/bison live in the
    device toolchain /data/service/hnp/bin);
  - ``PKG_CHECK_MODULES([UDEV], [libudev])`` is a hard configure-time check.
    eudev/3.2.14 publishes a ``libudev.pc`` (pkg_config_name=libudev) so
    PkgConfigDeps satisfies it; the UDEV_CFLAGS/UDEV_LIBS precious variables
    are also passed explicitly as a belt-and-braces (worker conan 2.29 does not
    always land ``tc.configure_args`` on the configure line);
  - the generated configure's ``umask 077`` is relaxed to 022 (E114: HMDFS
    forces setgid, and a 0700 config.status temp dir is not writable even by
    its owner), and TMPDIR points at the writable build folder;
  - autoreconf/configure/make run with ``env -u CONFIG_SHELL SHELL=/bin/sh``
    because the ohos-aarch64 profile exports CONFIG_SHELL=/data/service/hnp/bin/
    bash, whose getcwd() fails on HMDFS paths (E386 family);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - ``/etc/usbauth.conf`` is overridable through $USBAUTH_CONFIG (patch 0001):
    HarmonyOS mounts /etc as a read-only HMFS image, so the default path is
    kept but a consumer can point the parser at a writable location.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


class LibusbauthConfigparserConan(ConanFile):
    name = "libusbauth-configparser"
    version = "1.0.5"
    description = ("libusbauth-configparser - config-file parser for the usbauth "
                   "USB firewall (flex/bison lexer+grammar and a small C API)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/kochstefan/usbauth-all"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # configure.ac hard-checks PKG_CHECK_MODULES([UDEV], [libudev]); the
        # library also links it (LIBADD = $(UDEV_LIBS)) and calls
        # udev_device_get_parent / _get_sysattr_value.  eudev/3.2.14 ships
        # libudev.pc + libudev.so, so it satisfies both configure and link.
        self.requires("eudev/3.2.14")

    def build_requirements(self):
        # git snapshot with no configure: autoreconf -fi bootstraps it.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libusbauth-configparser is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["1.0.5"], strip_root=True)
        # The pinned archive is the usbauth-all monorepo; lift the package
        # subdirectory up to the source root so autotools sees a self-contained
        # tree (configure.ac / Makefile.am / src / data).
        sub = os.path.join(self.source_folder, "libusbauth-configparser")
        for name in os.listdir(sub):
            shutil.move(os.path.join(sub, name), os.path.join(self.source_folder, name))
        os.rmdir(sub)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        # Inject automake/libtool (tool_requires) bin dirs into the conanbuild
        # PATH; a clean CI PATH cannot see them otherwise ("aclocal: not found").
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # Generate libudev.pc for the configure-time PKG_CHECK_MODULES([UDEV]).
        PkgConfigDeps(self).generate()

    def _udev_paths(self):
        eudev = self.dependencies["eudev"]
        inc = eudev.cpp_info.includedirs[0].replace("\\", "/")
        lib = eudev.cpp_info.libdirs[0].replace("\\", "/")
        return inc, lib

    def build(self):
        _prepare_autotools_env()
        # configure.ac declares AC_CONFIG_MACRO_DIRS([m4]) and Makefile.am sets
        # ACLOCAL_AMFLAGS = -I m4, but the git snapshot ships no m4/ directory
        # (the project uses no custom macros).  Create it so aclocal -I m4 does
        # not warn/fail on the missing directory.
        os.makedirs(os.path.join(self.source_folder, "m4"), exist_ok=True)
        # E386 family: the profile [buildenv] exports CONFIG_SHELL=…/hnp/bash,
        # whose getcwd() fails on HMDFS paths; autoconf re-execs itself through
        # CONFIG_SHELL, so it must be cleared for autoreconf/configure.
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi",
                 cwd=self.source_folder, env="conanbuild")
        # E114: HMDFS forces setgid; `umask 077 && mktemp -d` yields a
        # drwx--S--- dir that is not writable even by its owner.  Relax the
        # generated configure's umask 077 to 022.
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            with open(cfg, "rb") as handle:
                data = handle.read()
            if b"umask 077" in data:
                with open(cfg, "wb") as handle:
                    handle.write(data.replace(b"umask 077", b"umask 022"))
        # E490: the adaptation path may strip exec bits from autotools helpers.
        for helper in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "compile", "depcomp", "test-driver", "ylwrap",
                       "ltmain.sh"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        # E114: keep temp files off the read-only /tmp (HMFS).
        os.environ["TMPDIR"] = self.build_folder
        inc, lib = self._udev_paths()
        autotools = Autotools(self)
        # tc.configure_args do not always land on the configure line under the
        # worker's conan 2.29, so the precious vars and triplets are passed
        # explicitly (libatasmart precedent).
        autotools.configure(args=[
            "UDEV_CFLAGS=-I{}".format(inc),
            "UDEV_LIBS=-L{} -ludev".format(lib),
            "--host=aarch64-linux-ohos",
            "--build=aarch64-linux-ohos",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Upstream's install-exec-hook uses a bash-only `*.{la,a}` brace glob,
        # which /bin/sh leaves unexpanded — drop the libtool archives and any
        # static archive unconditionally so the package only carries headers,
        # the shared library and the pkg-config file.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith((".la", ".a")):
                    os.remove(os.path.join(libdir, name))
        for extra in ("share/doc", "share/man"):
            path = os.path.join(self.package_folder, extra)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = ["usbauth-configparser"]
        self.cpp_info.set_property("cmake_file_name", "libusbauth-configparser")
        self.cpp_info.set_property("cmake_target_name",
                                   "libusbauth-configparser::libusbauth-configparser")
        self.cpp_info.set_property("pkg_config_name", "libusbauth-configparser")
