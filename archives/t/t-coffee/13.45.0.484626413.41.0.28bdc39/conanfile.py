#!/usr/bin/env python3
"""Conan recipe for t-coffee 13.45.0.484626413.41.0.28bdc39 on HarmonyOS PC.

T-COFFEE (Tree-based Consistency Objective Function for Alignment Evaluation) is
a progressive multiple-sequence-alignment program from the Centre de Regulacio
Genomica, Barcelona (Cedric Notredame).  The upstream distribution ships one
self-contained C program: ``t_coffee_source/`` holds 58 ``.c`` files under
``util_lib/ io_lib/ dp_lib/ fastal/ km_coffee/ dev_lib/ t_coffee_lib/`` plus a
23-line hand-written ``makefile``.  There is no configure step, no external
library (only libc + libm) and no test suite; the alignment matrices are compiled
in from ``matrices.h``.  Everything else in the tarball (``example/``, ``doc/``,
``mcoffee/``, the Perl helper scripts and the prebuilt ``bin/linux/t_coffee``) is
documentation, sample data or a foreign-architecture binary and is not packaged.

OHOS notes
----------
* ``-x c++`` is mandatory, not cosmetic.  The upstream makefile sets ``CC=g++``,
  i.e. it compiles the ``.c`` files **as C++**.  Both clang drivers key the
  language off the file extension, so ``clang++ foo.c`` would still compile C
  and the tree then fails to compile at all: ``io_lib/io_structures.h:299`` uses
  the injected class name ``Alignment`` inside ``struct Alignment`` (before the
  trailing ``typedef struct Alignment Alignment;``), and ``aln2prf`` /
  ``seq2msa`` are deliberately declared twice with different signatures, which is
  only legal as C++ overloading.  ``-x c++`` restores upstream semantics.
* ``-O0 -fsigned-char`` mirror Debian's ``debian/rules`` for the very same source
  (``DEB_CFLAGS_MAINT_APPEND+=-O0`` "to avoid crash in test suite" and
  ``-fsigned-char`` "for architectures such as arm").  Both were re-verified
  here independently of Debian: with ``-O1``..``-O3`` the program dies with
  SIGSEGV inside the ``proba_pair`` library (reproducible with g++ -O3 on
  x86_64 too, so it is an upstream optimiser-sensitive defect, not an OHOS
  issue), and the OHOS clang defaults to ``-fno-signed-char`` while upstream's
  x86_64 gcc is signed-char.
* One patch is required, for a clang-specific reason: see
  ``patches/0001-missing-return-in-non-void-functions.patch``.  30 non-void
  functions fall off their end (C++ UB).  clang lowers that to llvm
  ``unreachable``, which the AArch64 backend emits as ``brk #1`` (SIGTRAP), so
  the unpatched binary dies inside ``set_nproc()`` while ``batch_main()`` is
  still printing its parameter dump.  gcc emits an ordinary epilogue there, which
  is why upstream never saw it.  The patch only appends ``return <zero>;``;
  after it the ``-O0`` binary drops from 31 ``brk #1`` sites to 1 (the libc++abi
  ``__shim_type_info`` stub, unreachable at run time) and emits CLUSTAL W output
  byte-identical to a g++ ``-O0 -fsigned-char`` x86_64 reference build.
* The build links only ``-lm``; the resulting OHOS ELF needs just ``libc.so``.
* ``TMalign`` (the sibling Fortran program) is a separate ``make`` target driven
  by an undeclared ``$(FCC)`` and needs gfortran, which the OHOS NDK does not
  ship, so only the ``t_coffee`` target is built.  ``-run_name``/``-method``
  dispatch to it is out of scope for this package.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TCoffeeConan(ConanFile):
    name = "t-coffee"
    version = "13.45.0.484626413.41.0.28bdc39"
    description = (
        "T-COFFEE: progressive multiple sequence alignment by tree-based "
        "consistency objective function (CRG Barcelona, Cedric Notredame)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://www.tcoffee.org"
    url = "https://www.tcoffee.org"
    topics = ("bioinformatics", "alignment", "msa", "genomics")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"t-coffee is validated on Linux/OHOS only, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _cflags(self):
        """Flags handed to the upstream makefile.

        ``-x c++`` is required because the sources are C++ despite the ``.c``
        extension (see the module docstring).  ``-O0`` and ``-fsigned-char`` are
        what Debian uses for this exact source and both are load-bearing: at
        ``-O1`` and above the program segfaults inside ``proba_pair`` (also with
        g++ on x86_64), and the OHOS clang defaults to unsigned char where
        upstream's x86_64 gcc is signed-char.
        """
        return "-x c++ -O0 -fsigned-char -Wno-write-strings"

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp") or (cc if cc.endswith("++") else cc + "++")
        # Upstream's makefile links with $(CC) and the sources need the C++
        # driver, so override CC with the C++ compiler and force the language
        # through CFLAGS (R33: never a bare ${CC} from the environment).
        #
        # LDFLAGS: clang++ links libc++ dynamically by default, which puts
        # libc++_shared.so into DT_NEEDED.  That shared C++ runtime is not part
        # of the platform (R26; same treatment as fairy-stockfish and
        # graphviz), so the C++ runtime is linked statically and the packaged
        # binary ends up needing libc.so only.  Upstream's makefile ignores
        # LDFLAGS, hence patches/0002, which inserts $(LDFLAGS) on the link
        # line and changes nothing else.
        self.run(shlex.join(["make", "-j1", "t_coffee",
                             f"CC={cxx}",
                             f"CFLAGS={self._cflags()}",
                             "LDFLAGS=-static-libstdc++"]),
                 cwd=os.path.join(self.source_folder, "t_coffee_source"),
                 env="conanbuild")

    def package(self):
        src = os.path.join(self.source_folder, "t_coffee_source")
        copy(self, "t_coffee", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
