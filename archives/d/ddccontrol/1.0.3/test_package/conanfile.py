#!/usr/bin/env python3
"""test_package for ddccontrol 1.0.3 — runs the installed `ddccontrol` binary.

ddccontrol installs libddccontrol + headers, but the honest consumer check is
to invoke the installed tool the way a user would (appres precedent:
conanfile.py + test.sh, no CMake).  All asserted paths return BEFORE any
device or D-Bus access:

* main() prints the version banner unconditionally, before getopt() runs;
* `-h` and the bare invocation both reach usage() and exit(1) while still in
  argument parsing — before ddcci_init(), before the D-Bus proxy, before the
  first open() of /dev/i2c-* (which does not exist on this host anyway, see
  notes.md capability disclosure).

Runtime deps (libxml2/glib/libintl .so) are injected through VirtualRunEnv.
"""
import os

from conan import ConanFile


class DdccontrolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True is required, not decorative: VirtualRunEnv only composes
        # runenv_from_cpp_info (which is what puts <pkg>/bin on PATH) under
        # `if require.run:`, and Require.run defaults to FALSE
        # (requires.py: `_default_if_none(self._run, False)`) for a static
        # `library` package like this one — round-7 first error verbatim:
        # `test.sh: line 26: ddccontrol: command not found`.  Contrast proof
        # from the generated conanrunenv: PATH listed libxml2/glib/gettext
        # (shared -> run=True) but NOT pciutils (static -> run=False); appres
        # passed only because it is package_type="application".  Repo
        # precedent: 29 test_package conanfiles use exactly this (alive/2.0.3,
        # depqbf/5.01, imageworsener/1.3.5, ...).
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries, and HMDFS
        # setgid directories leave bash's getcwd() unreliable, so run through
        # bash with PWD seeded (E386 family, appres precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.run(f'cd "{cwd}" && PWD="{cwd}" "{bash}" test.sh', env="conanrun")
