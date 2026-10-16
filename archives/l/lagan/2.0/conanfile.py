#!/usr/bin/env python3
"""Conan recipe for LAGAN toolkit 2.0 — plain Makefile C/C++ application.

LAGAN is a bioinformatics toolkit for local, global, and multiple
alignment of DNA sequences (lagan, mlagan, shuffle-lagan, chaos, glocal
plus a set of utilities), built from a plain top-level Makefile that
delegates to src/Makefile.  It is NOT an autotools/CMake project.

Key build facts:
  * The sources are pure C/C++ and only link -lm; there are no external
    dependencies (no Boost, despite the task-pool note).
  * src/Makefile hardcodes `CC = gcc $(CFLAGS)` / `CPP = g++ $(CFLAGS)`
    and its `all` target recurses into glocal/ with a hardcoded g++.
    The explicit binary targets are therefore built (not `all`) so the
    cross compilers can be overridden on the make command line, and
    glocal/ is built separately with CC/CLINKER overrides.
  * The upstream tarball ships a prebuilt Mach-O `prolagan` in the root;
    the make target ../prolagan overwrites it with the freshly built
    binary, which is what gets packaged.
  * The perl wrappers locate the binaries via $LAGAN_DIR, so the package
    keeps binaries, scripts, and data files under a single root (bin/);
    runenv sets LAGAN_DIR=<package>/bin.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LaganConan(ConanFile):
    name = "lagan"
    version = "2.0"
    description = (
        "LAGAN toolkit: local, global, and multiple alignment of DNA "
        "sequences (lagan, mlagan, shuffle-lagan, chaos, glocal, utils)"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://lagan.stanford.edu/lagan_web"
    url = ""  # CI fills this
    topics = ("bioinformatics", "alignment", "dna")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value))

    def _compiler(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get(key, default)

    def build(self):
        apply_conandata_patches(self)

        copy(
            self,
            "*",
            src=self.source_folder,
            dst=self.build_folder,
        )

        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")

        # Modern clang/GCC default to -fno-common: the tentative definition
        # `int indeces[256];` in src/thrtrie.h is included from both fchaos.c
        # and thrtrie.c, which the linker then rejects as duplicate symbols.
        # -fcommon restores the pre-C17 merging behavior (same fix distros
        # applied after the GCC 10 -fno-common default change).
        common_flag = " -fcommon"

        src_dir = os.path.join(self.build_folder, "src")
        targets = (
            "../anchors ../chaos ../order ../mlagan ../prolagan "
            "../utils/bin2mf ../utils/bin2bl ../utils/cextract "
            "../utils/cstat ../utils/contigorder ../utils/getbounds "
            "../utils/getcontigpos ../utils/getlength ../utils/getoverlap "
            "../utils/rc ../utils/seqmerge ../utils/scorealign "
            "../utils/scorecontigs ../utils/fa2xfa ../utils/Glue "
            "../utils/dotplot ../utils/overlay"
        )

        # `all` in src/Makefile recurses into glocal/ with a hardcoded
        # g++; build the explicit binary targets instead so CC/CPP can
        # be overridden from the command line.
        self.run(
            "make -C {} CC={} CPP={} {}".format(
                self._quote(src_dir),
                self._quote(cc + " -O3" + common_flag),
                self._quote(cxx + " -O3" + common_flag),
                targets,
            ),
            env="conanbuild",
        )
        self.run(
            "make -C {} CC={} CLINKER={}".format(
                self._quote(os.path.join(src_dir, "glocal")),
                self._quote(cxx + " -O3" + common_flag),
                self._quote(cxx),
            ),
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=os.path.join(self.source_folder, "Readmes"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        bin_dir = os.path.join(self.package_folder, "bin")

        for name in ("anchors", "chaos", "order", "mlagan", "prolagan", "glocal"):
            copy(
                self,
                name,
                src=self.build_folder,
                dst=bin_dir,
                keep_path=False,
            )

        # utils/ = the built C utilities plus the upstream perl scripts
        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "utils"),
            dst=os.path.join(bin_dir, "utils"),
            keep_path=False,
        )

        # perl entry scripts, score matrices, and sample data
        for name in (
            "lagan.pl", "slagan.pl", "slagan-mfa.pl", "rechaos.pl",
            "anal_gloc.pl", "xmfa2mfa.pl", "Utils.pm",
            "nucmatrix.txt", "blosum62.txt", "blosum62s.txt",
            "sample.fasta", "sample.params",
        ):
            copy(
                self,
                name,
                src=self.source_folder,
                dst=bin_dir,
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.buildenv_info.prepend_path(
            "PATH",
            os.path.join(self.package_folder, "bin"),
        )

        self.runenv_info.prepend_path(
            "PATH",
            os.path.join(self.package_folder, "bin"),
        )

        self.runenv_info.define(
            "LAGAN_DIR",
            os.path.join(self.package_folder, "bin"),
        )
