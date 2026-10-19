#!/usr/bin/env python3
"""Consumer test for xmedcon/0.26.1-gtk3.

xmedcon ships the headless `medcon` CLI and the GTK+3 `xmedcon` GUI.  The
assertions live in test_xmedcon.py so the package ships a real test source
file (CI L0c requires one).  See that file for the headless strategy.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class XmedconTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["xmedcon"]
        bindir = dep.cpp_info.bindirs[0]
        medcon = os.path.join(bindir, "medcon")
        xmedcon = os.path.join(bindir, "xmedcon")
        test_script = os.path.join(self.source_folder, "test_xmedcon.py")
        # env="conanrun" puts dependency libdirs on LD_LIBRARY_PATH; the
        # GTK+3 closure (and libmdc) needs it; child python inherits it.
        self.run('"%s" "%s" "%s" "%s"' % (sys.executable, test_script, medcon, xmedcon),
                 env="conanrun")
