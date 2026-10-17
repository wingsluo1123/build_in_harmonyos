#!/usr/bin/env python3
"""Conan recipe - pd-purepd 0.1.1 (Pure Data abstraction library, no compilation).

purepd re-implements standard Pure Data objects as abstractions written purely
in Pd.  Upstream's Makefile (the Pd library template 1.0.6) has an empty
SOURCES list and no check/test target: there is nothing to compile, the library
is data plus the help patches that document it.  The recipe therefore packages
the abstraction set with the libdir layout upstream installs it to
(`objectsdir = $(prefix)/lib/pd-externals`, `LIBRARY_NAME = purepd`) and leaves
the actual verification to test_package, which loads the abstractions in a real
Pd interpreter (see test_package/verify_purepd.py).
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class PdPurepdConan(ConanFile):
    name = "pd-purepd"
    version = "0.1.1"
    description = "Pure Data library of standard objects re-implemented as vanilla Pd abstractions"
    license = "GPL-2.0-or-later"
    homepage = "https://puredata.info/"
    url = "https://sourceforge.net/projects/pure-data/files/libraries/purepd/"
    topics = ("puredata", "pd", "audio", "abstractions", "vanilla")

    # No binaries are produced and the packaged files are architecture
    # independent, so the package is declared as a header-library (the same
    # choice the other data/header only recipes of this repository make) and
    # its package_id is cleared below.
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    no_copy_source = True

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="purepd-0.1.1.tar.gz",
            strip_root=True,
        )

    def package_id(self):
        self.info.clear()

    def package(self):
        # Mirror upstream `make libdir_install`: the abstractions, their help
        # patches and the libdir meta file go to <prefix>/lib/pd-externals/purepd
        # together with the two documentation files; the Makefile itself is not
        # installed upstream either.
        pd_libdir = os.path.join(self.package_folder, "lib", "pd-externals", "purepd")
        copy(self, "*.pd", src=self.source_folder, dst=pd_libdir)
        copy(self, "README.txt", src=self.source_folder, dst=pd_libdir)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=pd_libdir)
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Pure-Pd content: no compiled library and no headers.  The
        # abstractions are exposed both as the upstream libdir and as a
        # resource directory, which is what a consumer needs to put on Pd's
        # search path (`pd -path ...` / `libpd_add_to_search_path`).
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["lib/pd-externals"]
