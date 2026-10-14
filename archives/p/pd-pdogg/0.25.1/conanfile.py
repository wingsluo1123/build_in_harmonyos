#!/usr/bin/env python3
"""Conan recipe for pd-pdogg 0.25.1 (Pure Data Ogg/Vorbis objects).

pdogg (Olaf Matthes) provides Ogg/Vorbis streaming and file objects for Pure
Data: ``oggamp~`` (streaming client), ``oggcast~`` (streaming server),
``oggread~`` (file reader) and ``oggwrite~`` (file recorder).  It uses
upstream's old "Pd library template" Makefile and links against libvorbis /
libogg.

OHOS notes
----------
* The ``puredata`` Conan package does not expose the Pd API header
  ``m_pd.h``, so this recipe fetches the matching Pure Data source release
  (0.54-1) and adds its ``src/`` to the include path.
* The legacy template decides the target from ``uname -s``; OHOS reports
  ``HarmonyOS``, so ``UNAME=Linux`` is forced on the ``make`` command line
  (selects the ``pd_linux`` extension and shared-object link flags).
* The template computes its vorbis flags through ``pkg-config``; this recipe
  supplies ``ALL_CFLAGS`` / ``ALL_LDFLAGS`` / ``ALL_LIBS`` on the command line
  from the Conan dependency graph instead, so no ``pkg-config`` is needed.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

PD_SRC_URLS = [
    "https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1",
    "https://github.com/pure-data/pure-data/archive/refs/tags/0.54-1.tar.gz",
]
PD_SRC_SHA256 = "19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353"

MIN_CLASSES = 4


class PdPdoggConan(ConanFile):
    name = "pd-pdogg"
    version = "0.25.1"
    description = "pdogg: Ogg/Vorbis streaming and file objects for Pure Data"
    license = "LGPL-2.1-or-later"
    homepage = "https://puredata.info"
    url = ""

    # Installs Pd external shared objects (lib/pd-externals/*.pd_linux), not
    # command-line programs: a library, not an application.  Declaring it as an
    # application made the CI R38 gate demand a CLI commands.json.
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libvorbis/1.3.7")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-pdogg OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def _get_pd_api(self):
        pd_dir = os.path.join(self.source_folder, "pd-api")
        os.makedirs(pd_dir, exist_ok=True)
        last = None
        for url in PD_SRC_URLS:
            try:
                get(self, url=url, sha256=PD_SRC_SHA256,
                    filename="pure-data-0.54-1.tar.gz", strip_root=True,
                    destination=pd_dir)
                return
            except Exception as e:  # noqa: BLE001
                last = e
                self.output.warning("pure-data download failed from %s: %s"
                                    % (url, e))
        raise ConanInvalidConfiguration(
            "could not download pure-data source tree: %s" % last)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._get_pd_api()

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _dep_flags(self):
        """Return (-I flags, -L flags, -l flags) from libvorbis + libogg."""
        incs, libdirs, libs = [], [], []
        for _, dep in self.dependencies.items():
            if dep.ref.name not in ("libvorbis", "libogg"):
                continue
            try:
                ci = dep.cpp_info.aggregated_components()
            except Exception:
                ci = dep.cpp_info
            pkg = dep.package_folder
            for i in getattr(ci, "includedirs", []):
                incs.append(i if os.path.isabs(i) else os.path.join(pkg, i))
            for l in getattr(ci, "libdirs", []):
                libdirs.append(l if os.path.isabs(l) else os.path.join(pkg, l))
            for lib in getattr(ci, "libs", []):
                libs.append(lib)
        return (sorted(set(incs)), sorted(set(libdirs)), sorted(set(libs)))

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        pdinc = os.path.join(self.source_folder, "pd-api", "src")
        if not os.path.isfile(os.path.join(pdinc, "m_pd.h")):
            raise ConanInvalidConfiguration(
                "Pd API header not found: " + os.path.join(pdinc, "m_pd.h"))

        incs, libdirs, libs = self._dep_flags()
        if not libdirs:
            raise ConanInvalidConfiguration(
                "could not resolve libvorbis/libogg flags from dependencies")
        inc_flags = " ".join('-I"%s"' % d for d in [pdinc] + incs)
        lib_flags = " ".join('-L"%s"' % d for d in libdirs)
        lib_flags += " " + " ".join("-l%s" % l for l in libs)

        all_cflags = '%s -DPD -fPIC -O2 -w' % inc_flags
        all_ldflags = "-shared -fPIC"
        all_libs = "%s -lc -lm" % lib_flags

        self.run('make -j1 CC="%s" UNAME=Linux ALL_CFLAGS="%s" ALL_LDFLAGS="%s" ALL_LIBS="%s"'
                 % (cc, all_cflags, all_ldflags, all_libs),
                 cwd=self.source_folder, env="conanbuild")
        produced = sorted(f for f in os.listdir(self.source_folder)
                          if f.endswith(".pd_linux"))
        if len(produced) < MIN_CLASSES:
            raise ConanInvalidConfiguration(
                "expected at least %d externals, produced %d"
                % (MIN_CLASSES, len(produced)))
        self.output.info("built %d Pd externals" % len(produced))

    def package(self):
        ext = os.path.join(self.package_folder, "lib", "pd-externals")
        copy(self, "*.pd_linux", self.source_folder, ext)
        copy(self, "*-help.pd", self.source_folder, ext)
        copy(self, "pdogg-meta.pd", self.source_folder, ext)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
