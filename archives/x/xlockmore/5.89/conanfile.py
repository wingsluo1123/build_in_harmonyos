#!/usr/bin/env python3
"""Conan recipe for xlockmore 5.89 — X Window System screen lock/screensaver.

xlockmore is the maintained version of xlock, a screen locker and screensaver
for the X Window System. It provides dozens of animation modes and is built
with GNU Autotools (configure + make).

OHOS cross-build notes:
  - The upstream tarball ships a generated configure script; no autoconf
    bootstrap is needed.
  - configure's bundled config.guess/config.sub do not recognise OHOS, so
    --host and --build must be given explicitly (precedent: xdx, meterec).
  - Most optional features (OpenGL, Mesa, GTK, Motif, XPM, ImageMagick,
    sound daemons, etc.) are disabled to keep the dependency chain minimal
    and within what the ohpcd registry provides.
  - libpng is currently not declared as a conan dependency: even though
    configure detects it, the modes that use it compile out when XPM is
    disabled (--without-xpm), and ldd shows no libpng DT_NEEDED entry.
    If future testing reveals a runtime dependency, add libpng to requires().
  - xlockmore links against libcrypt; on OHOS/musl this is provided by the
    C library itself, so no separate libcrypt conan package is needed.
  - HMDFS umask fix: configure and config.status use `umask 077` for temp
    directories; on HMDFS the resulting permissions deny access to the
    build process (precedent: xdx, quagga, vimpc, istgt). Replace with
    `umask 022`.
  - Parallel make (-jN) fails on HMDFS workers due to jobserver mkfifo
    being denied; use -j1 (precedent: xdx, meterec, vfu).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XlockmoreConan(ConanFile):
    name = "xlockmore"
    version = "5.89"
    description = "xlockmore — maintained version of xlock, X Window System screen lock and screensaver"
    license = "MIT"
    homepage = "https://www.sillycycle.com/xlockmore.html"
    url = "https://www.sillycycle.com/xlock"
    topics = ("x11", "screensaver", "screenlock", "xlock")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("libx11/1.8.13", force=True)
        self.requires("libxext/6.4.0.1")
        self.requires("libxmu/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            headers={"User-Agent": "Conan/2.0"})

    def _fix_hmdfs_umask(self, path):
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "umask 077" in content:
            save(self, path, content.replace("umask 077", "umask 022"))
            self.output.info("HMDFS umask fix applied to %s" % os.path.basename(path))

    def _x11_pkg_paths(self):
        inc_dirs = []
        lib_dirs = []
        for dep_name in ("libx11", "libxext", "libxmu", "libxt",
                         "libsm", "libice", "xorgproto",
                         "libxcb", "libxau", "libxdmcp"):
            dep = self.dependencies.get(dep_name)
            if dep is None:
                continue
            pkg = dep.package_folder
            if pkg and os.path.isdir(os.path.join(pkg, "include")):
                inc_dirs.append(os.path.join(pkg, "include"))
            if pkg and os.path.isdir(os.path.join(pkg, "lib")):
                lib_dirs.append(os.path.join(pkg, "lib"))
        return inc_dirs, lib_dirs

    def generate(self):
        tc = AutotoolsToolchain(self)
        inc_dirs, lib_dirs = self._x11_pkg_paths()
        x_includes = ":".join(inc_dirs) if inc_dirs else ""
        x_libraries = ":".join(lib_dirs) if lib_dirs else ""
        tc.configure_args.extend([
            "--host=aarch64-linux-gnu",
            "--build=aarch64-unknown-linux-gnu",
        ])
        if x_includes:
            tc.configure_args.append("--x-includes=" + x_includes)
        if x_libraries:
            tc.configure_args.append("--x-libraries=" + x_libraries)
        tc.configure_args.extend([
            "--without-motif",
            "--without-athena",
            "--without-xaw",
            "--without-xpm",
            "--without-libpng",
            "--without-opengl",
            "--without-mesa",
            "--without-gltt",
            "--without-ttf",
            "--without-ftgl",
            "--without-freetype",
            "--without-magick",
            "--without-rplay",
            "--without-nas",
            "--without-esound",
            "--without-gtk",
            "--without-gtk2",
            "--without-dpms",
            "--without-xinerama",
            "--without-dtsaver",
            "--disable-gtktest",
        ])
        tc.cflags.append("-UHAVE_SHADOW")
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        self._fix_hmdfs_umask(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        self._fix_hmdfs_umask(os.path.join(self.build_folder, "config.status"))
        self._undef_shadow_in_config_h()
        self._disable_shadow_in_passwd_c()
        self._strip_system_x11_includes()
        autotools.make(args=["-j1"])

    def _undef_shadow_in_config_h(self):
        config_h = os.path.join(self.build_folder, "config.h")
        if not os.path.isfile(config_h):
            return
        with open(config_h, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "#define HAVE_SHADOW" in content:
            content = content.replace("#define HAVE_SHADOW 1",
                                     "/* #undef HAVE_SHADOW */")
            save(self, config_h, content)
            self.output.info("undef'd HAVE_SHADOW in config.h")

    def _disable_shadow_in_passwd_c(self):
        passwd_c = os.path.join(self.source_folder, "xlock", "passwd.c")
        if not os.path.isfile(passwd_c):
            return
        with open(passwd_c, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "!defined( HAVE_SHADOW )" in content:
            content = content.replace(
                "#if defined( __linux__ ) && defined( __ELF__ ) && !defined( HAVE_SHADOW )",
                "#if 0  /* OHOS: shadow password not available, force-disable */"
            )
            save(self, passwd_c, content)
            self.output.info("disabled shadow fallback in passwd.c")

    def _strip_system_x11_includes(self):
        for root, dirs, files in os.walk(self.build_folder):
            for name in files:
                if name == "Makefile":
                    path = os.path.join(root, name)
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    if " -I/usr/include" in content:
                        content = content.replace(" -I/usr/include", "")
                        save(self, path, content)
                        self.output.info(
                            "stripped -I/usr/include from %s" % path)

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=[
            "-j1",
            "INSTALL=cp",
            "INSTALL_PROGRAM=cp",
            "INSTALL_SCRIPT=cp",
            "INSTALL_DATA=cp",
            "INSTPGMFLAGS=",
        ])
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
