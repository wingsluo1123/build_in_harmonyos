#!/usr/bin/env python3
"""Conan recipe for pd-markex 0.85 (Pure Data externals).

markex is a collection of miscellaneous Pure Data externals by Mark Danks
(20 classes: abs~, average, counter, hsv2rgb, reson~, vectorpack, ...).
It ships upstream's old "Pd library template" Makefile, which produces one
``<class>.pd_linux`` shared object per class.

OHOS notes
----------
* The ``puredata`` Conan package is an *application*: it installs ``pd`` and
  its data dir but does not expose the Pd API headers (``m_pd.h``).  This
  recipe therefore fetches the matching upstream Pure Data source release
  (0.54-1, the release ``puredata/0.54.1`` is built from) and points the
  compiler at ``src/``.
* The legacy template decides the target from ``uname -s``; OHOS reports
  ``HarmonyOS`` which matches no branch, so ``UNAME=Linux`` is forced on the
  ``make`` command line (the Linux branch selects the ``pd_linux`` extension
  and the shared-object link flags).
* ``CFLAGS`` is supplied on the command line so the template's ``+=`` appends
  (``-O6`` etc.) are overridden, keeping the build flags under our control.
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

MIN_CLASSES = 20


class PdMarkexConan(ConanFile):
    name = "pd-markex"
    version = "0.85"
    description = "markex: miscellaneous Pure Data externals by Mark Danks"
    license = "GPL-2.0-or-later"
    homepage = "https://puredata.info"
    url = ""

    # Installs Pd external shared objects (lib/pd-externals/*.pd_linux), not
    # command-line programs: a library, not an application.  Declaring it as an
    # application made the CI R38 gate demand a CLI commands.json.
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-markex OHOS adaptation is validated on Linux/OHOS, not "
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

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        pdinc = os.path.join(self.source_folder, "pd-api", "src")
        if not os.path.isfile(os.path.join(pdinc, "m_pd.h")):
            raise ConanInvalidConfiguration(
                "Pd API header not found: " + os.path.join(pdinc, "m_pd.h"))
        cflags = "-I%s -DPD -fPIC -O2 -w" % pdinc
        self.run('make -j1 CC="%s" UNAME=Linux CFLAGS="%s"'
                 % (cc, cflags),
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
        copy(self, "markex-meta.pd", self.source_folder, ext)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
