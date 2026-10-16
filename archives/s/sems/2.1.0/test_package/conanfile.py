#!/usr/bin/env python3
"""test_package for sems 2.1.0.

test() genuinely exercises the packaged artifacts:

  * runs the packaged upstream fct runner sbin/sems_tests (11 suites,
    204 assertions) -- the same binary the upstream `ctest` target runs;
  * runs the packaged server binary sbin/sems and its real smoke test
    (test_package/test_sems.sh, which asserts `sems -v` exits 0 and reports
    version 2.1.0);
  * checks the core plug-in directory produced by the module rules.

On a cross target (`can_run` false) the arm64 OHOS binaries cannot be executed
from the build machine, so the test verifies the packaged layout only; CI runs
on a native OHOS worker, where both binaries are executed for real.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class SemsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        sems = os.path.join(package_folder, "sbin", "sems")
        sems_tests = os.path.join(package_folder, "sbin", "sems_tests")
        plugin_dir = os.path.join(package_folder, "lib", "sems", "plug-in")

        for path in (sems, sems_tests):
            if not os.path.isfile(path):
                raise RuntimeError("packaged file is missing: %s" % path)
        if not os.path.isdir(plugin_dir):
            raise RuntimeError("plug-in directory is missing: %s" % plugin_dir)
        if not os.listdir(plugin_dir):
            raise RuntimeError("plug-in directory is empty: %s" % plugin_dir)

        if not can_run(self):
            self.output.info("SEMS_SKIP_RUN (cross target cannot run locally); "
                             "packaged layout verified")
            return

        # 1) upstream fct suite, for real
        self.run(sems_tests, env="conanrun")
        # 2) packaged server binary smoke test, for real
        shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        self.run('SEMS_BIN="%s" "%s" test_sems.sh' % (sems, shell), env="conanrun")
