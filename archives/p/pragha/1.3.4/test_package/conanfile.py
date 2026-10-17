#!/usr/bin/env python3
"""Consumer test for the packaged pragha executable.

pragha is a GTK3 GUI music player; HarmonyOS PC has no X server, so the test
drives the installed binary through the headless paths the adaptation
provides: --version/--help (upstream CLI contract), --selftest (the
adaptation's new HarmonyOS consumer case exercising production code:
musicobject round trip/dup/compare, playlist format detection, sqlite3 and
GStreamer runtime binding), and the expected no-display failure that proves
the packaged binary actually loads the GTK3/GLib stack it links.

The test always runs the shell harness (no can_run guard): CI's destructive
negative gate (L1e) moves the package artifacts away and re-runs this test,
which must then fail because the binary it invokes is gone.
"""
import os
import shutil

from conan import ConanFile


class PraghaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_pragha.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["pragha"].package_folder, "bin", "pragha"
        )
        script = os.path.join(self.source_folder, "test_pragha.sh")
        shell = shutil.which("sh") or "/system/bin/sh"
        self.run(
            f'"{shell}" "{script}" "{executable}"',
            env="conanrun",
        )
