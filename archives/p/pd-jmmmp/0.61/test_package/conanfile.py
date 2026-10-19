#!/usr/bin/env python3
"""Conan consumer test for pd-jmmmp 0.61.

The package carries no compiled code, so the consumer verifies the packaged
abstraction set structurally and - where a Pd interpreter can run - loads the
abstractions in a real Pd and checks their behaviour.  All assertions live in
verify_jmmmp.py so that the data layer and the runtime layer report one
combined result.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PdJmmmpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "verify_jmmmp.py", "jmmmp_instantiate.pd", "jmmmp_smoke.pd", \
        "jmmmp_inventory.txt"

    def requirements(self):
        self.requires(self.tested_reference_str)
        if str(self.settings.os) in ("Linux", "OHOS"):
            # pd-jmmmp is architecture-independent data and stays installable
            # without Pd; the interpreter that can load the abstractions is
            # needed only by this consumer test, hence a test-only requirement.
            self.requires("puredata/0.56.5")

    def test(self):
        command = [
            '"%s"' % self._python(),
            '"%s"' % os.path.join(self.source_folder, "verify_jmmmp.py"),
            "--jmmmp-dir",
            '"%s"' % self._jmmmp_dir(),
            "--patches",
            '"%s"' % self.source_folder,
            "--pd-externals",
            '"%s"' % self._pd_externals_dir(),
        ]
        if can_run(self) and str(self.settings.os) in ("Linux", "OHOS"):
            command += ["--pd", '"%s"' % self._pd_binary()]
        else:
            self.output.info(
                "no runnable Pd interpreter for this configuration: verifying the "
                "packaged data only")
        self.run(" ".join(command), env="conanrun")

    def _python(self):
        executable = sys.executable or shutil.which("python3")
        if not executable:
            raise ConanException("no python interpreter available to run verify_jmmmp.py")
        return executable

    def _res_dir(self):
        dependency = self.dependencies[self.tested_reference_str]
        resdirs = dependency.cpp_info.resdirs
        if not resdirs:
            raise ConanException("pd-jmmmp does not declare a resource directory")
        return resdirs[0]

    def _jmmmp_dir(self):
        return os.path.join(self._res_dir(), "jmmmp")

    def _pd_externals_dir(self):
        return self._res_dir()

    def _pd_binary(self):
        dependency = self.dependencies["puredata"]
        bindirs = dependency.cpp_info.bindirs
        if not bindirs:
            raise ConanException("puredata does not declare a bin directory")
        binary = os.path.join(bindirs[0], "pd")
        if not os.path.isfile(binary):
            raise ConanException("pd interpreter not found at %s" % binary)
        return binary
