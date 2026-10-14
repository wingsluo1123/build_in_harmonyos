#!/usr/bin/env python3
"""Conan recipe for xsetroot 1.1.3 — the X.Org root-window utility.

xsetroot is a single-file X11 client (``xsetroot.c``) built with Autotools.  The
package product is the command-line executable ``bin/xsetroot``, so this is an
"application" package (R38: a software-level ``commands.json`` is required).

OHOS adaptation notes (full record in notes.md):

  * The upstream tarball ships a pre-generated ``configure`` (Autoconf 2.71), so
    no autoconf/xorg-macros bootstrap is needed.  It is driven through the
    CI-verified HarmonyOS Autotools pattern shared by the other X.Org recipes in
    this repository (libxcursor / libxmu): configure runs in cross-compiling
    mode with ``--host=aarch64-linux-ohos``.
  * Upstream's ``configure`` sets ``umask 077`` while creating its helper
    directories; on the OHOS worker that leaves them unreadable for the
    subsequent ``make``, so the script is run through a build-local copy with
    ``umask 022`` (the libxcursor workaround).
  * ``configure.ac`` runs ``PKG_CHECK_MODULES(XSETROOT, [xmuu x11 xbitmaps
    xcursor xproto >= 7.0.25])``.  Two of those modules cannot come from the
    artifact repository:

      - ``xbitmaps`` is not published there at all.  xsetroot only needs
        ``<X11/bitmaps/gray>`` from it (an ``#include``, not a linked library),
        so the canonical 87-byte data file is vendored under ``files/`` — the
        same data shim already merged for motif/2.3.8 (byte-identical to
        upstream xbitmaps-1.1.3/gray).

      - ``xmuu`` is a *different* module than the published ``libxmu``
        package provides.  libxmu/1.3.1.1 pins ``libx11/1.8.13`` graph-wide
        (its own recipe explains: libxt's OHOS libtool shadow build hard-requires
        libX11.la, which libx11/6.4.0 removes), while libxcursor/1.2.3 ships only
        on the ``libx11/6.4.0`` track — the two published binaries are mutually
        exclusive, and rebuilding either track trips an unrelated recipe bug.
        xsetroot needs exactly one symbol from libXmuu (``XmuCursorNameToIndex``,
        plus the ``X11/Xmu/CurUtil.h`` declaration), so the two upstream files
        that implement it (``CursorName.c``, ``Lower.c``) and their three headers
        are vendored under ``files/`` and compiled into a private ``libXmuu.a``.
        This is the same vendoring approach the merged ``xeyes`` recipe uses for
        libXmu; the vendored bytes are identical to upstream libXmu-1.3.1.

    ``PKG_CHECK_MODULES``' documented escape hatch is used instead of
    pkg-config: presetting ``XSETROOT_CFLAGS``/``XSETROOT_LIBS`` makes pkg.m4
    adopt them and skip the pkg-config query (the ``XEYES_CFLAGS``/``XEYES_LIBS``
    pattern from xeyes).
  * ``xsetroot -version`` prints ``PACKAGE_STRING`` and exits 0 without touching
    the X server, which gives the consumer test in test_package/ a real,
    display-less behavioural assertion.

Upstream ships **no test suite** (no ``TESTS``/``check_PROGRAMS`` in
Makefile.am), so per TEST_QUALITY_SPEC the consumer suite in test_package/ is
the adapted test coverage; MANIFEST.yml declares that explicitly.
"""

import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# The libXmuu module xsetroot needs is two upstream translation units.
VENDORED_XMUU_SOURCES = ("CursorName.c", "Lower.c")


class XsetrootConan(ConanFile):
    name = "xsetroot"
    version = "1.1.3"
    description = ("X.Org utility that sets the root window attributes of an X "
                   "display (background, cursor, name)")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xsetroot"
    url = "https://gitlab.freedesktop.org/xorg/app/xsetroot"
    topics = ("x11", "xorg", "root-window", "utility")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # Ship the vendored xbitmaps data file and the vendored libXmuu sources under
    # files/; export_conandata_patches() alone would not copy them.
    exports_sources = "files/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The published libx11/6.4.0 + libxcursor/1.2.3 + xorgproto/2025.1
        # combination resolves entirely from prebuilt binaries.  libxmu is
        # deliberately NOT required: it pins libx11/1.8.13 (see module docstring),
        # and its "xmuu" spelling is provided here by the vendored libXmuu instead.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxcursor/1.2.3", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    # R32: only Linux-family targets are supported.
    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xsetroot supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-docs")
        # Make the vendored headers (<X11/Xmu/CurUtil.h>) and the xbitmaps data
        # file (<X11/bitmaps/gray>) visible to the compiler.
        toolchain.extra_cflags.append(f"-I{self._files_root()}")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        xmuu_dir = self._build_vendored_xmuu() if str(self.settings.os) == "OHOS" \
            else self._build_vendored_xmuu_native()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._generate_ohos_configure()
                self._configure(xmuu_dir, ohos=True)
                self._run_ohos("make -j1")
            else:
                self._configure(xmuu_dir, ohos=False)
                Autotools(self).make(args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Application package: the deliverable is the CLI executable.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ── helpers ──────────────────────────────────────────────────────────────
    def _files_root(self):
        """Directory holding the vendored headers, data file and sources."""
        return Path(self.export_sources_folder, "files").as_posix()

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _dependency_flags(self):
        """Include/link flags for the X11 libraries taken from Conan.

        xorgproto is header-only and supplies <X11/Xfuncproto.h>, which the
        vendored <X11/Xmu/*.h> headers include.
        """
        includes, libraries = [], []
        for name in ("libx11", "libxcursor", "xorgproto"):
            dependency = self.dependencies[name]
            for include in dependency.cpp_info.includedirs:
                path = include if os.path.isabs(include) \
                    else os.path.join(dependency.package_folder, include)
                includes.append(f"-I{path}")
            for libdir in dependency.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) \
                    else os.path.join(dependency.package_folder, libdir)
                libraries.append(f"-L{path}")
        return " ".join(includes), " ".join(libraries)

    def _build_vendored_xmuu(self):
        """Compile the two vendored libXmuu units into a private static archive."""
        files_root = Path(self._files_root())
        output = Path(self.build_folder, "xmuu")
        output.mkdir(parents=True, exist_ok=True)
        # The vendored headers pull <X11/Xfuncproto.h> (xorgproto) and
        # <X11/cursorfont.h> (libx11), so the Conan include dirs must be on the
        # command line: the vendored files live under export_sources, which
        # AutotoolsDeps does not add to the toolchain flags.
        includes, _ = self._dependency_flags()
        objects = []
        for name in VENDORED_XMUU_SOURCES:
            source = files_root / name
            if not source.is_file():
                raise ConanException(f"vendored libXmuu source is missing: {source}")
            obj = output / f"{name[:-2]}.o"
            self.run(
                f'$CC $CPPFLAGS $CFLAGS -I{shlex.quote(files_root.as_posix())} '
                f'{includes} -c {shlex.quote(source.as_posix())} '
                f'-o {shlex.quote(obj.as_posix())}',
                cwd=self.build_folder, env="conanbuild")
            objects.append(obj)
        archive = output / "libXmuu.a"
        self.run(
            f'$AR rcs {shlex.quote(archive.as_posix())} '
            + " ".join(shlex.quote(o.as_posix()) for o in objects),
            cwd=self.build_folder, env="conanbuild")
        return output

    def _build_vendored_xmuu_native(self):
        """Same as _build_vendored_xmuu() for native (non-OHOS) builds."""
        return self._build_vendored_xmuu()

    def _configure(self, xmuu_dir, ohos):
        """Run configure, escaping PKG_CHECK_MODULES with preset flags.

        configure.ac asks for the modules xmuu x11 xbitmaps xcursor xproto.  The
        published packages cover x11/xcursor/xproto, xbitmaps is vendored as a
        header/data shim and xmuu as the private libXmuu.a.  Presetting
        XSETROOT_CFLAGS/XSETROOT_LIBS makes pkg.m4 adopt them verbatim and skip
        the pkg-config lookup (the XEYES_CFLAGS/XEYES_LIBS escape from xeyes).
        """
        includes, libraries = self._dependency_flags()
        cflags = f"-I{self._files_root()} {includes}"
        libs = (f"-L{xmuu_dir.as_posix()} -lXmuu {libraries} -lXcursor -lX11")
        arguments = [
            f"XSETROOT_CFLAGS={cflags}",
            f"XSETROOT_LIBS={libs}",
        ]
        if ohos:
            configure_args = [
                f"--srcdir={self.source_folder}",
                "--host=aarch64-linux-ohos",
                *self._toolchain_configure_args(),
                *arguments,
            ]
            shell = "/system/bin/sh"
            if not os.path.isfile(shell):
                raise ConanInvalidConfiguration(
                    f"OHOS configure shell is missing: {shell}")
            joined = " ".join(shlex.quote(a) for a in configure_args)
            self._run_ohos(f'"{shell}" "{self._ohos_configure_path()}" {joined}')
        else:
            autotools = Autotools(self)
            autotools.configure(args=arguments)

    def _toolchain_configure_args(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-docs")
        toolchain.extra_cflags.append(f"-I{self._files_root()}")
        return list(toolchain.configure_args)

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated = self._ohos_configure_path()
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(content.replace(needle, "umask 022"),
                             encoding="utf-8", newline="\n")

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")
