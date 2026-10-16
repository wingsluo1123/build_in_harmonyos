#!/usr/bin/env python3
"""test_package for xcwd 0-2.gbpe2c777c — consumer test against the *packaged* binary.

The product of this recipe is the command-line program ``bin/xcwd``, so the
consumer suite (R34) really executes the packaged executable and asserts on its
observable behaviour.  Every assertion reads the artifacts shipped inside the
Conan package folder — nothing here is a print-only stub.

``test_xcwd.py`` is the harness and is driven from :meth:`test` with a real
``self.run()``.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class XcwdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep Conan's generated files (conanbuild.sh / conanrun.sh / …) inside
        # the test build folder instead of polluting the archived recipe dir.
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def test(self):
        dependency = self.dependencies["xcwd"]
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        executable = os.path.join(dependency.package_folder, bindirs[0], "xcwd")
        harness = os.path.join(self.recipe_folder, "test_xcwd.py")

        if not os.path.isfile(harness):
            raise AssertionError(f"consumer harness missing: {harness}")

        if not can_run(self):
            raise AssertionError(
                "cannot run the packaged xcwd binary on this host — the "
                "consumer suite must execute the artifact, not skip it")

        # Real execution of the packaged program, driven by a real harness.
        self.run(f'python3 "{harness}" "{executable}" "{self.build_folder}"',
                 env="conanrun")
