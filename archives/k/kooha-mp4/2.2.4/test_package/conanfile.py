#!/usr/bin/env python3
"""Consumer test for kooha-mp4 2.2.4.

Runs test.sh (via the configured shell), which exercises the packaged
kooha binary headless:
  1. `kooha --version` — the early-exit path added by patch 0001 (before
     gtk/gst/resource init; zenity 4.2.2 E252 precedent), asserting the
     upstream version string.
  2. gresource bundle loads (glib-compile-resources product is valid).
  3. gschema compiles strict (GSettings schema is valid).
  4. ELF traits: AArch64 machine + OHOS musl PT_INTERP + code signature
     (the OHOS-specific must-haves; below/0.11.0 precedent).

Full GUI recording needs a display session, a running xdg-desktop-portal
with the screencast interface, and a window system — none exist on the
Broadway-only gtk4 build (see MANIFEST.yml).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class KoohaMp4TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: kooha binary runs on OHOS device")
            return
        # R34: actually run the packaged kooha binary via test.sh.
        # Resolve the tested package folder explicitly: test.sh runs from a
        # copied test build folder, so $0-relative paths don't reach the
        # package payload (conan 2 layout).
        package_dir = self.dependencies[self.tested_reference_str].package_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'KOOHA_PACKAGE_DIR="{package_dir}" {bash} test.sh',
            env="conanrun")
