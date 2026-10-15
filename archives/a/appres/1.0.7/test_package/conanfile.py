#!/usr/bin/env python3
"""test_package for appres 1.0.7 — runs the installed `appres` binary.

appres ships no library and no headers, so a consumer cannot link against it;
the honest consumer check is to invoke the installed tool the way a user would
(2048.c / aa3d precedent: conanfile.py + test.sh, no CMake).

Exercised paths are `-version`, `-V` and `-help`, which return before any X
connection is attempted (verified on this device with DISPLAY unset: exit 0).
The bare invocation and the unknown-argument path do open a display and exit 1
with "Error: Can't open display" on a host with no X server; they are recorded
in notes.md instead of being asserted here.
"""
import os

from conan import ConanFile


class AppresTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries, and HMDFS
        # setgid directories leave bash's getcwd() unreliable, so run through
        # bash with PWD seeded (E386 family).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.run(f'cd "{cwd}" && PWD="{cwd}" "{bash}" test.sh', env="conanrun")
