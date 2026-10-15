#!/usr/bin/env python3
"""Consumer test for snac/2.93.

snac is a single-binary ActivityPub server; a real instance needs a data
directory and a listening socket, which the build sandbox does not provide.
The assertions live in test_snac.py so the package ships a real test source
file (CI L0c requires one; conanfile.py alone does not count).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SnacTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["snac"]
        bin_path = os.path.join(dep.cpp_info.bindirs[0], "snac")
        test_script = os.path.join(self.source_folder, "test_snac.py")
        self.run('"%s" "%s" "%s"' % (sys.executable, test_script, bin_path),
                 env="conanrun")
