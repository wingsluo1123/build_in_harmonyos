#!/usr/bin/env python3
"""test_package for gammastep 2.0.9 — runs the installed `gammastep` binary.

gammastep is an `application` package (CLI only, no library/headers), so the
honest consumer check is to invoke the installed tool the way a user would
(appres / ddccontrol precedent: conanfile.py + test.sh, no CMake).

Every asserted path returns inside argument parsing and **before** any display
backend is initialized:

* `-V` prints PACKAGE_STRING and ``exit(EXIT_SUCCESS)``;
* `-h` calls print_help() and ``exit(EXIT_SUCCESS)``;
* `-m list` calls print_method_list() and ``exit(EXIT_SUCCESS)`` — this is the
  strong one: the printed list is generated from the compile-time
  ``gamma_methods[]`` array, so it proves which backends were actually
  compiled in;
* `-m <unknown>` writes "Unknown adjustment method" and returns -1 → rc=1.

Nothing here opens /dev/dri, connects to a Wayland compositor or an X server
(see notes.md for the runtime capability disclosure).
"""
import os

from conan import ConanFile


class GammastepTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True is required, not decorative: VirtualRunEnv only puts
        # <pkg>/bin on PATH for requires with `run=True` (Require.run defaults
        # to False).  ddccontrol/1.0.3 round-7 first error was verbatim
        # `test.sh: line 26: ddccontrol: command not found` without it.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries, and HMDFS
        # setgid directories leave bash's getcwd() unreliable, so run through
        # bash with PWD seeded (E386 family; appres/ddccontrol precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.run(f'cd "{cwd}" && PWD="{cwd}" "{bash}" test.sh', env="conanrun")
