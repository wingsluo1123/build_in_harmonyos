#!/usr/bin/env python3
"""Conan recipe for pd-pmpd 0.14.2 (Pure Data physical modelling).

pmpd (Physical Modelling for Pure Data, Cyrille Henry) is a collection of
externals simulating physical phenomena (masses, links, interactors, 2D/3D
sand/fluid/... ).  It is built with upstream's CMake build, which produces one
shared object per class; the classes are loaded by Pd at patch-load time.

OHOS notes
----------
* The ``puredata`` Conan package does not expose the Pd API header
  ``m_pd.h``, so this recipe fetches the matching Pure Data source release
  (0.54-1) and passes its ``src/`` as ``PUREDATA_INCLUDE_DIRS``.
* Upstream's CMake would name the objects with the multi-arch suffix
  (``.linux-arm64-32.so``); ``PUREDATA_SUFFIX`` is forced to ``.pd_linux`` so
  the objects are found by Pd's standard loader.
* ``git_info.cmake`` degrades gracefully when the source tree is not a git
  checkout (it reports ``...-NOTFOUND``); no source modification is needed.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

PD_SRC_URLS = [
    "https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1",
    "https://github.com/pure-data/pure-data/archive/refs/tags/0.54-1.tar.gz",
]
PD_SRC_SHA256 = "19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353"

MIN_CLASSES = 32


class PdPmpdConan(ConanFile):
    name = "pd-pmpd"
    version = "0.14.2"
    description = "pmpd: Pure Data physical modelling externals (Cyrille Henry)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ch-nry/pd-pmpd"
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
                "pd-pmpd OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

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

    def generate(self):
        pdinc = os.path.join(self.source_folder, "pd-api", "src")
        if not os.path.isfile(os.path.join(pdinc, "m_pd.h")):
            raise ConanInvalidConfiguration(
                "Pd API header not found: " + os.path.join(pdinc, "m_pd.h"))
        tc = CMakeToolchain(self)
        tc.variables["PUREDATA_INCLUDE_DIRS"] = pdinc
        tc.variables["PUREDATA_SUFFIX"] = ".pd_linux"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        produced = [f for _, _, files in os.walk(self.build_folder)
                    for f in files if f.endswith(".pd_linux")]
        if len(produced) < MIN_CLASSES:
            raise ConanInvalidConfiguration(
                "expected at least %d externals, produced %d"
                % (MIN_CLASSES, len(produced)))
        self.output.info("built %d Pd externals" % len(produced))

    def package(self):
        ext = os.path.join(self.package_folder, "lib", "pd-externals")
        for root, _, files in os.walk(self.build_folder):
            for f in files:
                if f.endswith(".pd_linux"):
                    copy(self, f, root, ext)
        copy(self, "*-help.pd", self.source_folder, ext)
        copy(self, "pmpd-meta.pd", self.source_folder, ext)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
