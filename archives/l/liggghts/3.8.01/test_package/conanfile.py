"""Consumer-side test for liggghts/3.8.01.

The package ships an application (``bin/lmp_mpi``), so the consumer test runs
that binary on a deterministic DEM deck and asserts on the solver output - see
``test_liggghts.sh``.  ``VirtualRunEnv`` puts the package ``bin/`` and the
runtime library paths of the dependency graph (mpich) into the environment.
"""

import os
import shutil

from conan import ConanFile


class LiggghtsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _bash():
        """OHOS /system/bin/sh (mksh) does not execute ELF binaries; use bash."""
        shell = os.environ.get("CONFIG_SHELL")
        if shell and os.path.isfile(shell):
            return shell
        found = shutil.which("bash")          # device profile puts HNP bash on PATH
        return found or "/data/service/hnp/bash"

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        # Consumer-side functional test: run the packaged engine on a
        # deterministic DEM deck (see test_liggghts.sh).
        self.run(f"{self._bash()} test_liggghts.sh", env="conanrun")
        # HarmonyOS runtime behaviour: gzip-compressed data file (LAMMPS_GZIP),
        # insert/pack with -screen none (patch 0004 regression), 2 MPI ranks.
        self.run(f"{self._bash()} test_ohos_runtime.sh", env="conanrun")
        # HarmonyOS artifact properties: ELF architecture/PIE/interpreter,
        # DT_NEEDED set, permissions, CLI smoke.
        self.run('python3 check_ohos.py "{}"'.format(dep.package_folder),
                 env="conanrun")
