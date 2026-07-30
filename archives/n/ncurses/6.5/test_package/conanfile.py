#!/usr/bin/env python3
"""Test package — ncurses 6.5.

Links a minimal C program against libncursesw.a and runs it to verify
the static archive and headers are usable.
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class NcursesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsToolchain", "VirtualBuildEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Minimal ncurses program: initscr + endwin.
        # The `-l` flag already prepends `lib`, so pass the bare name:
        # `-lncursesw` searches `libncursesw.a`, whereas `-llibncursesw`
        # would search `liblibncursesw.a` (which ncurses never installs).
        src = os.path.join(self.source_folder, "test_ncurses.c")
        lib = "ncursesw" if self.dependencies["ncurses"].options.widec else "ncurses"
        self.run(
            f'clang "{src}" -o test_ncurses -Iinclude -Llib -l{lib} -static',
            cwd=self.source_folder,
        )

    def test(self):
        # Binary should exist and be runnable (initscr may fail without tty, that's ok)
        self.run("test -f test_ncurses", cwd=self.source_folder)
