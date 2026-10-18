#!/usr/bin/env python3
"""Conan test_package for xine-ui 0.99.14.

xine-ui ships an application (R34: the test must really consume it), so the L1
test drives the packaged ``xine`` / ``xine-check`` binaries end-to-end rather
than compiling against headers.  Everything runs headless: the keymap emitter
and the config loader do not need an X display, while actual playback does and
is therefore covered by the packaged-data / diagnostics cases instead.
"""
import os

from conan import ConanFile


class XineTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
