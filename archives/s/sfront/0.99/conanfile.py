#!/usr/bin/env python3
"""Conan recipe for sfront 0.99 - MPEG-4 Structured Audio (MP4-SA) to C translator.

sfront compiles an MP4-SA bitstream, or a plain-text SAOL orchestra plus a SASL /
MIDI score, into a standalone C program that synthesises or processes audio when
it is executed.  Upstream ships a hand-written Makefile in ``src/`` plus a second
one in ``src/lib/`` whose ``libmaker`` code generator regenerates the five
``*lib.c`` / ``*lib.h`` runtime-library sources that the translator embeds into
every program it emits.

OHOS notes
----------
* The upstream Makefiles hard-code ``CC=gcc``, ``MODEL=-m32`` and
  ``ECHECK=-ansi -Wall``.  ``-m32`` cannot be honoured on AArch64, so the recipe
  overrides ``CFLAGS`` wholesale and reads the compiler out of
  ``tools.build:compiler_executables`` (R33 - never bare ``${CC}``).
* ``SLOWSCHED = -fno-schedule-insns`` is a GCC-only scheduling hint; clang only
  accepts it with an "optimization flag ... is not supported" warning, so the
  recipe clears it instead of letting it into every compile line.
* Upstream's build is driven through ``src/lib/Makefile``, whose ``all`` target
  runs ``libmaker`` and then re-enters ``src/Makefile``.  Both are built with the
  same ``-j1`` because the nested make cannot inherit a jobserver over HMDFS
  (E074/E525).
* ``src/Makefile`` also has ``parser.tab.c: parsehelp.c parser.y tree.h`` with a
  ``-bison`` recipe.  The official tarball already ships the bison 2.3 output
  (``parser.tab.c`` / ``parser.tab.h``), and extraction order decides whether make
  considers it stale, which would make the build depend on a bison that is not a
  declared dependency.  The recipe therefore touches the shipped files so the
  pre-generated parser is authoritative.  Regenerating with bison 3.8.2 was
  cross-checked and produces the same translator output (see notes.md).
* ``-static`` keeps the delivered translator self-contained: it starts both
  natively on an AArch64 OHOS worker and under ``qemu-aarch64`` on an x86 build
  host, with no dynamic loader in the picture.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SfrontConan(ConanFile):
    name = "sfront"
    version = "0.99"
    description = ("MPEG-4 Structured Audio (MP4-SA) translator: compiles SAOL "
                   "orchestras / MP4-SA bitstreams into standalone C audio programs")
    license = "BSD-3-Clause AND GFDL-1.3-or-later"
    homepage = "https://john-lazzaro.github.io/sa/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "mp4-sa", "saol", "synthesis", "transpiler", "codec")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sfront is validated on Linux/OHOS only, not {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # Upstream CFLAGS are "$(MODEL) $(OPT) $(DBUG) $(ECHECK)" = "-m32 -O2 -g
        # -ansi -Wall"; -m32 is dropped (AArch64 has no 32-bit ABI here) and the
        # implicit-function-declaration error keeps the C89-era sources honest
        # about POSIX declarations that __STRICT_ANSI__ would hide.
        cflags = "-O2 -Wall -Werror=implicit-function-declaration -static"
        src = os.path.join(self.source_folder, "src")
        # Ship the tarball's pre-generated bison output; see module docstring.
        self.run("touch parser.tab.c parser.tab.h", cwd=src)
        # src/lib/Makefile builds libmaker, regenerates the *lib.[ch] runtime
        # sources and then descends into src/Makefile to link bin/sfront.
        self.run(shlex.join(["make", "-j1", f"CC={cc}", f"CFLAGS={cflags}",
                             "SLOWSCHED=", "LINKLIB=-lm"]),
                 cwd=os.path.join(src, "lib"), env="conanbuild")

    def package(self):
        src = self.source_folder
        copy(self, "sfront", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Upstream carries macOS resource-fork leftovers in examples/ and book/
        # (6 .DS_Store plus 32 ._* files); they are not part of the software.
        junk = ["*.DS_Store", "._*"]
        # The SAOL standard library (Slib) and the resonance extensions the
        # generated programs are written against.
        copy(self, "*", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "share", "sfront", "lib"))
        # Upstream example orchestras / scores: the only executable specification
        # this release ships in place of an automated test suite.
        copy(self, "*", src=os.path.join(src, "examples"),
             dst=os.path.join(self.package_folder, "share", "sfront", "examples"),
             excludes=junk)
        docs = os.path.join(self.package_folder, "share", "doc", "sfront", "html")
        for entry in ("README.HTML", "index.html"):
            copy(self, entry, src=src, dst=docs, keep_path=False)
        for entry in ("book", "sfman", "copyright"):
            copy(self, "*", src=os.path.join(src, entry),
                 dst=os.path.join(docs, entry), excludes=junk)
        copy(self, "*", src=os.path.join(src, "copyright"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
