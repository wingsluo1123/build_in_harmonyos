#!/usr/bin/env python3
"""Conan recipe for abcmidi 20260609 on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AbcmidiConan(ConanFile):
    name = "abcmidi"
    version = "20260609"
    description = "Command-line tools for converting and processing ABC music notation"
    license = "GPL-2.0-or-later"
    homepage = "https://abcmidi.sourceforge.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        src = self.source_folder
        out = self.build_folder
        cflags = "-O2 -DANSILIBS"

        programs = {
            "abc2midi": [
                "parseabc.c", "store.c", "genmidi.c", "midifile.c",
                "queues.c", "parser2.c", "stresspat.c", "music_utils.c",
            ],
            "midi2abc": ["midifile.c", "midi2abc.c"],
            "abc2abc": ["parseabc.c", "toabc.c", "music_utils.c"],
            "mftext": ["midifile.c", "mftext.c", "crack.c"],
            "yaps": [
                "parseabc.c", "yapstree.c", "drawtune.c", "debug.c",
                "pslib.c", "position.c", "parser2.c", "music_utils.c",
            ],
            "midicopy": ["midicopy.c"],
            "abcmatch": [
                "abcmatch.c", "matchsup.c", "parseabc.c", "music_utils.c",
            ],
            "midistats": ["midifile.c", "midistats.c"],
        }

        for program, sources in programs.items():
            source_args = " ".join(
                '"{}"'.format(os.path.join(src, source)) for source in sources
            )
            output = os.path.join(out, program)
            self.run(
                '"{}" {} -I"{}" {} -lm -o "{}"'.format(
                    cc, cflags, src, source_args, output
                )
            )

    def package(self):
        for program in (
            "abc2midi", "midi2abc", "abc2abc", "mftext", "yaps",
            "midicopy", "abcmatch", "midistats",
        ):
            copy(
                self,
                program,
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "bin"),
            )
        copy(
            self,
            "*.1",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
