#!/usr/bin/env python3
"""Conan test_package for rezound (graphical audio editor, L1).

ReZound ships no library: the artefact under test is the installed
``bin/rezound`` program plus its ``share/rezound`` data files, so the L1 test
drives that program for real (R34) instead of a placeholder.  ``test.sh``
checks the packaged layout, the OpenHarmony aarch64 ELF header and executes the
binary far enough to prove the whole dynamic dependency chain
(libFOX-1.6 -> libX11/libXext, ...) resolves.
"""
import os

from conan import ConanFile


class RezoundTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
