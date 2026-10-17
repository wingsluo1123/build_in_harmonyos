#!/usr/bin/env python3
"""Conan recipe for SpliX 2.0.1 — CUPS filter driver for QPDL (SPL2) printers.

SpliX provides the CUPS filters ``rastertoqpdl`` (CUPS raster -> QPDL/SPL2) and
``pstoqpdl`` (PostScript -> CUPS raster -> QPDL) together with the matching PPD
and DRV printer description files for Samsung, Xerox, Dell, Lexmark and Toshiba
printers that speak QPDL / SPL2.

Upstream build system
---------------------
Upstream ships a hand-written GNU make setup (``Makefile`` + ``module.mk`` +
``rules.mk``) instead of autotools/cmake.  It hard-codes ``CC := gcc`` /
``CXX := g++`` and obtains the CUPS compile/link flags by running
``cups-config`` from ``PATH``.  For an OHOS cross build that cannot work: the
``cups-config`` shipped inside the Conan CUPS package points at the build
machine's ``/usr/include`` and ``/lib``.

``patches/0001`` therefore replaces the ``cups-config`` back-tick calls with the
standard ``CPPFLAGS`` / ``LDFLAGS`` / ``LIBS`` variables, which
``AutotoolsDeps`` fills with the include dirs, library dirs and the complete,
correctly ordered library list of ``cups`` (and its own static dependencies,
e.g. OpenSSL/zlib/libiconv) and ``libjbig``.  The compiler drivers and the
CUPS install directories are passed on the ``make`` command line (a command
line assignment also overrides the ``CC := gcc`` / ``CXX := g++`` defaults and
avoids every remaining ``cups-config`` call).  The patch introduces no platform
macro and no platform conditional.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps
from conan.tools.layout import basic_layout


# CUPS on-disk locations that upstream compiles into pstoqpdl
# (-DRASTERDIR / -DCUPSPPD / -DCUPSPROFILE).  They are the CUPS defaults of the
# target platform.
_CUPS_FILTER_DIR = "/usr/lib/cups/filter"
_CUPS_MODEL_DIR = "/usr/share/cups/model"
_CUPS_DRV_DIR = "/usr/share/cups/drv"
_CUPS_PROFILE_DIR = "/usr/share/cups/profiles"


class SplixConan(ConanFile):
    name = "splix"
    version = "2.0.1"
    description = (
        "SpliX — CUPS filter driver (rastertoqpdl / pstoqpdl) and PPD/DRV "
        "description files for QPDL (SPL2) Samsung, Xerox, Dell, Lexmark and "
        "Toshiba printers"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/OpenPrinting/splix"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Upstream builds in-source (the makefile writes .defs.mk, optimized/
        # objects and the two executables next to the sources).
        basic_layout(self, src_folder=".", build_folder=".")

    def requirements(self):
        # libcups + libcupsimage, and their server side static dependencies.
        self.requires("cups/2.4.19")
        # JBIG-KIT: libjbig85 is linked by the JBIG algorithm (algo0x15.cpp).
        self.requires("libjbig/2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers
    @property
    def _make_program(self):
        return self.conf.get("tools.gnu:make_program", default="make", check_type=str)

    @property
    def _jobs(self):
        return self.conf.get("tools.build:jobs", default=1, check_type=int)

    def _compilers(self):
        """R33: compiler drivers come from the Conan configuration, never from
        bare shell environment variables."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") if compilers else None
        cxx = compilers.get("cpp") if compilers else None
        if not cc or not cxx:
            raise ConanException(
                "tools.build:compiler_executables must define both the 'c' and "
                "the 'cpp' compiler driver for this recipe"
            )
        return cc, cxx

    def _make_arguments(self):
        cc, cxx = self._compilers()
        # DESTDIR safety net: rules.mk's `install` target honours $(DESTDIR)
        # and writes the filters into $(DESTDIR)$(CUPSFILTER) (etc.). Pointing
        # it at a writable staging dir means that even if `install` is ever
        # reached, it never touches the read-only system CUPS tree
        # (/usr/lib/cups, /usr/share/cups) that fails on OHOS with
        # "mkdir: '/usr/lib/cups': Read-only file system".
        destdir = os.path.join(self.build_folder, "cups-staging")
        return [
            "-j{}".format(self._jobs),
            "V=1",
            "DESTDIR={}".format(destdir),
            "CC={}".format(cc),
            "CXX={}".format(cxx),
            "CUPSFILTER={}".format(_CUPS_FILTER_DIR),
            "CUPSPPD={}".format(_CUPS_MODEL_DIR),
            "CUPSDRV={}".format(_CUPS_DRV_DIR),
            "CUPSPROFILE={}".format(_CUPS_PROFILE_DIR),
        ]

    # -------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        # Build only the `all` goal: it compiles rastertoqpdl/pstoqpdl into
        # optimized/ (module.mk sets MODE := optimized). We deliberately do NOT
        # run the default `install` goal — on OHOS the CUPS install dirs
        # (/usr/lib/cups/filter, /usr/share/cups/model, ...) are read-only and
        # `make install` dies with "mkdir: '/usr/lib/cups': Read-only file
        # system". package() below gathers the binaries from optimized/ and the
        # PPD/DRV files directly, so `install` is both unnecessary and harmful.
        command = " ".join(
            ['"{}"'.format(self._make_program), "all"] + self._make_arguments()
        )
        # AutotoolsDeps computes CPPFLAGS / LDFLAGS / LIBS for cups + libjbig
        # (including cups' transitive static requirements) in dependency order.
        deps = AutotoolsDeps(self)
        with deps.vars().apply():
            self.run(command, cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # The two CUPS filters (built in optimized/ because module.mk sets
        # MODE := optimized, i.e. TARGETDIR := optimized).
        for tool in ("rastertoqpdl", "pstoqpdl"):
            copy(
                self,
                tool,
                src=os.path.join(self.source_folder, "optimized"),
                dst=os.path.join(self.package_folder, "bin"),
            )
        # Printer description files: the release tarball already contains the
        # pre-generated PPDs and the DRV data (make drv/ppd would need `recode`).
        # ppd/ holds the vendor set; the 12 top level files (ml2160/ml2165/
        # ml3310*) of the release are not in ppd/, so they are taken as well.
        model_dir = os.path.join(self.package_folder, "share", "cups", "model", "splix")
        copy(self, "*.ppd", src=os.path.join(self.source_folder, "ppd"), dst=model_dir)
        copy(self, "*.ppd", src=self.source_folder, dst=model_dir)
        copy(
            self,
            "*.drv",
            src=os.path.join(self.source_folder, "ppd"),
            dst=os.path.join(self.package_folder, "share", "cups", "drv"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share/cups"]
