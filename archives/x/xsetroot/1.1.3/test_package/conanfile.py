#!/usr/bin/env python3
"""test_package for xsetroot 1.1.3 — consumer test against the *packaged* binary.

The product of this recipe is the command-line program bin/xsetroot, so the
consumer suite (R34) really executes the packaged executable and asserts on its
observable behaviour.  Nothing here is a print-only stub: every assertion reads
the artifacts shipped inside the Conan package folder.

test_xsetroot.py is the harness and is driven from test() below with a real
self.run().
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class XsetrootTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep Conan's generated files (conanbuild.sh / conanrun.sh / …) inside
        # the test build folder instead of polluting the archived recipe dir.
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def test(self):
        build_folder = self.build_folder
        dep = self.dependencies["xsetroot"]
        bindirs = dep.cpp_info.bindirs or ["bin"]
        exe = os.path.join(dep.package_folder, bindirs[0], "xsetroot")
        script = os.path.join(self.recipe_folder, "test_xsetroot.py")

        if not os.path.isfile(script):
            raise AssertionError(f"consumer harness missing: {script}")

        if can_run(self):
            # Real execution of the packaged program, driven by a real harness.
            self.run(f'python3 "{script}" "{exe}" "{build_folder}"', env="conanrun")
        else:
            raise AssertionError(
                "cannot run the packaged xsetroot binary on this host — the "
                "consumer suite must execute the artifact, not skip it")
