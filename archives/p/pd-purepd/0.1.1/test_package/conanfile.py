#!/usr/bin/env python3
"""Conan consumer test for pd-purepd 0.1.1.

The package carries no compiled code, so the consumer test verifies the
packaged abstraction set structurally and - where a Pd interpreter can run -
loads the abstractions in Pd and checks their behaviour.  All assertions live
in verify_purepd.py so that the data layer and the runtime layer report one
combined result.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PdPurepdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "verify_purepd.py", "purepd_instantiate.pd", "purepd_smoke.pd"

    def requirements(self):
        self.requires(self.tested_reference_str)
        if str(self.settings.os) in ("Linux", "OHOS"):
            # pd-purepd is architecture independent data and stays installable
            # without Pd; the interpreter that can load the abstractions is
            # needed only by this consumer test, hence a test-only requirement.
            self.requires("puredata/0.56.5")

    def test(self):
        command = [
            '"%s"' % self._python(),
            '"%s"' % os.path.join(self.source_folder, "verify_purepd.py"),
            "--purepd-dir",
            '"%s"' % self._purepd_dir(),
        ]
        if can_run(self) and str(self.settings.os) in ("Linux", "OHOS"):
            command += [
                "--patches",
                '"%s"' % self.source_folder,
                "--pd",
                '"%s"' % self._pd_binary(),
            ]
        else:
            self.output.info(
                "no runnable Pd interpreter for this configuration: verifying the packaged data only"
            )
        self.run(" ".join(command), env="conanrun")

    def _python(self):
        executable = sys.executable or shutil.which("python3")
        if not executable:
            raise ConanException("no python interpreter available to run verify_purepd.py")
        return executable

    def _purepd_dir(self):
        dependency = self.dependencies[self.tested_reference_str]
        resdirs = dependency.cpp_info.resdirs
        if not resdirs:
            raise ConanException("pd-purepd does not declare a resource directory")
        return os.path.join(resdirs[0], "purepd")

    def _pd_binary(self):
        dependency = self.dependencies["puredata"]
        bindirs = dependency.cpp_info.bindirs
        if not bindirs:
            raise ConanException("puredata does not declare a bin directory")
        binary = os.path.join(bindirs[0], "pd")
        if not os.path.isfile(binary):
            raise ConanException("pd interpreter not found at %s" % binary)
        return binary
