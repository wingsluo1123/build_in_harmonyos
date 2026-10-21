#!/usr/bin/env python3
"""Conan test_package for pa-applet g20181009.

Verifies the installed binary: file/exec bit, ELF, RUNPATH, the DT_NEEDED set
(GTK3 + libpulse + libpulse-mainloop-glib + libnotify) and a real run of
`pa-applet --help`, which exits before gtk_init()/pulse connects.

R34: the test genuinely depends on the tested package — a package without the
binary (L1e destructive check) fails here.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PaAppletTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass  # application package — nothing to build, the binary is tested

    def test(self):
        binary = os.path.join(
            self.dependencies["pa-applet"].package_folder, "bin", "pa-applet")
        script = os.path.join(self.source_folder, "test_pa_applet.sh")
        self.run(f'bash "{script}" "{binary}"')
