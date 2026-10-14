#!/usr/bin/env python3
"""Consumer test for the packaged pseudo executables and libpseudo.so."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class PseudoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["pseudo"]
        bindir = dep.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        binary = os.path.join(bindir, "pseudo")
        script = os.path.join(self.source_folder, "test_pseudo.sh")
        # The client spawns its daemon from $PSEUDO_PREFIX/bin/pseudo, so the
        # consumer test needs the installed prefix, not a scratch directory.
        self.run(
            f'/bin/sh "{script}" "{binary}" "{dep.package_folder}"',
            env="conanrun",
        )
