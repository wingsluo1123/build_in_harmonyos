#!/usr/bin/env python3
"""Conan recipe - pd-jmmmp 0.61 (Pure Data GUI/utility abstraction library).

jmmmp is Joao Pais' collection of Pure Data abstractions for musical
performance: 72 abstractions plus 68 help patches, the libdir meta file, a
dozen data files that the abstractions load at run time and the example images
they display.  Upstream ships **no C/C++ source and no Makefile** - the whole
release is ``data only'' - so there is nothing to compile and nothing to link.

OHOS notes
----------
* Architecture independent content: the same package binary serves every
  profile, so ``package_id()`` is cleared and the recipe is declared as a
  header library (the pattern the other data-only recipes of this repository
  use, e.g. pd-purepd).
* Layout follows upstream/Debian: ``lib/pd-externals/jmmmp/`` holds the
  abstractions, the ``jmmmp-meta.pd`` libdir marker, the ``*.txt`` data files
  and the ``examples/`` image set (Debian's pd-jmmmp.install copies exactly
  these three groups to /usr/lib/pd/extra/jmmmp).
* 22 of the 72 abstractions reference classes from other Pd libraries
  (zexy, iemlib, iemmatrix, cyclone, ggee, list-abs, maxlib, mrpeach, Gem,
  ceammc, else, pd-ableton-link).  Those libraries are *runtime* prerequisites
  of a Pd installation, not Conan build dependencies: the package is useful
  without them (49 abstractions run on vanilla Pd alone) and none of them is
  needed to assemble or consume this package.  Debian expresses the same thing
  with ``Recommends``.  See notes.md for the per-abstraction map.
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class PdJmmmpConan(ConanFile):
    name = "pd-jmmmp"
    version = "0.61"
    description = ("jmmmp: Pure Data GUI and utility abstractions by Joao Pais "
                   "(72 abstractions, pure Pd data, no compiled code)")
    license = "BSD-3-Clause"
    homepage = "https://puredata.info"
    url = "https://sourceforge.net/projects/pure-data/files/libraries/jmmmp"
    topics = ("puredata", "pd", "audio", "abstractions", "gui", "data-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    no_copy_source = True

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="pd-jmmmp-0.61.tar.xz",
            strip_root=True,
        )

    def package_id(self):
        # Pure Pd data: no ABI, no architecture, one binary for every profile.
        self.info.clear()

    def package(self):
        # Mirror Debian's pd-jmmmp.install: *.pd + *.txt + examples/ go to
        # <prefix>/lib/pd/extra/jmmmp, which is the same libdir role as
        # <prefix>/lib/pd-externals/jmmmp here.
        pd_libdir = os.path.join(self.package_folder, "lib", "pd-externals", "jmmmp")
        copy(self, "*.pd", src=self.source_folder, dst=pd_libdir)
        copy(self, "*.txt", src=self.source_folder, dst=pd_libdir)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "examples"),
            dst=os.path.join(pd_libdir, "examples"),
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # No compiled library and no headers.  A consumer puts
        # <pkg>/lib/pd-externals/jmmmp on Pd's search path for the flat names and
        # <pkg>/lib/pd-externals for the "jmmmp/<name>" namespace form that some
        # upstream patches use.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["lib/pd-externals"]
