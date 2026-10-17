#!/usr/bin/env python3
"""Consumer test for termshark/2.4.0 (R34 substantial verification).

termshark ships an executable; the assertions live in test_termshark.py so
the package ships a real test source file (CI L0c requires one; conanfile.py
alone does not count).

Environment handling (important): termshark execs `tshark`, which is a
shared-library application needing its whole dependency closure on
LD_LIBRARY_PATH.  That path list must NOT be applied to this test process
itself — it poisons unrelated binaries (e.g. the interpreter running this
script: an injected libintl makes `libpython3.12.so` fail with
`libintl_gettext: symbol not found`).  So the recipe exports the paths as
plain variables and the test applies them only to the termshark/tshark
*child* processes.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class TermsharkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)
        # tshark is the runtime command dependency termshark execs.  It is
        # transitive via termshark, but declaring it here guarantees it is
        # part of this test's dependency graph so its bin/lib can be located.
        # Same root cause as snakeviz/2.2.2 needing an explicit tornado.
        self.requires("tshark/4.6.7")

    def generate(self):
        env = Environment()
        deps = self.dependencies

        pkg = deps[self.tested_reference_str.split("/")[0]].package_folder
        env.define("TERMSHARK_PACKAGE_ROOT", pkg)

        # tshark's bin directory (the command termshark execs).
        try:
            tshark_folder = deps["tshark"].package_folder
        except Exception:
            tshark_folder = ""
        if not tshark_folder:
            raise ConanInvalidConfiguration(
                "termshark test requires the tshark dependency to be in the graph")
        tshark_bin = os.path.join(tshark_folder, "bin")
        if not os.path.isdir(tshark_bin):
            raise ConanInvalidConfiguration(
                f"tshark bin directory not found in {tshark_folder}")
        env.define("TERMSHARK_TSHARK_BIN", tshark_bin)

        # tshark is a shared-library application: it needs its ENTIRE
        # dependency closure on LD_LIBRARY_PATH (tshark itself plus glib,
        # libgcrypt, libgpg-error, libxml2, zstd, brotli, ...).  Collect
        # every dependency's libdir so the test can build a child env.
        lib_dirs = []
        for dep in deps.values():
            # Guard FIRST: some dependencies (tool requires, skip binaries)
            # have package_folder=None and os.path.join would raise TypeError.
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                lib_dirs.append(libdir)
        # Keep order, drop duplicates.
        seen = []
        for d in lib_dirs:
            if d not in seen:
                seen.append(d)
        env.define("TERMSHARK_LIB_DIRS", os.pathsep.join(seen))

        # Exported as plain variables (not PATH/LD_LIBRARY_PATH) on purpose:
        # see the module docstring.
        env.vars(self).save_script("termshark_test_env")

    def test(self):
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_termshark.py")
        # NOTE: deliberately NOT passing "conanrun" — its LD_LIBRARY_PATH
        # would poison the interpreter running this test.  The test builds a
        # child env for the termshark/tshark subprocesses instead.
        self.run(f'"{sys.executable}" "{test_script}"',
                 env=["termshark_test_env"])
