import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class LaganTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["lagan"].package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_lagan.py")
        check = '"{}" "{}" --bin-dir "{}"'.format(sys.executable, script, bin_dir)

        # Phase 1 -- always runs, including for a cross build where
        # can_run() is False: the installed package must ship all 6
        # alignment binaries, the 17 compiled utilities, the perl wrappers
        # and the scoring matrices, and the ELFs must carry the executable
        # bit.  Deleting any packaged artifact makes this consumer test
        # fail, so it is a real gate rather than a smoke stub.
        self.run(check)

        # Phase 2 -- native target only: start the packaged ELFs and check
        # they print their documented usage banner.
        if can_run(self):
            self.run(check + " --run")