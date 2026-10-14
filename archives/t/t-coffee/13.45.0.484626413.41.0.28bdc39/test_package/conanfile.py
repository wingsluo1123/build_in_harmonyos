#!/usr/bin/env python3
"""Consumer tests for t-coffee 13.45.0.484626413.41.0.28bdc39.

Every runtime case really executes the packaged ``bin/t_coffee`` and asserts on
its output.  test.sh receives the absolute path of the packaged binary.

The artifact is an OHOS aarch64 ELF.  The CI profile runs on a real HarmonyOS PC,
so it executes natively there; on an x86_64 runner the same artifact is started
through ``qemu-aarch64`` when available, and when neither is possible the
runtime cases degrade to SKIP while the ELF/artifact assertions keep running
(the discipline archives/s/sockstat/0.4.2 uses).
"""
import os
import shlex

from conan import ConanFile


class TCoffeeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _t_coffee(self):
        folder = self.dependencies[self.tested_reference_str].package_folder
        return os.path.join(folder, "bin", "t_coffee")

    def test(self):
        script = os.path.join(self.recipe_folder, "test_t_coffee.sh")
        self.run(shlex.join(["bash", script, self._t_coffee()]), env="conanrun")
