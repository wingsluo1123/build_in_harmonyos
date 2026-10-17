from pathlib import Path
import shlex
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class SolvateConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "verify_checkpoint.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("Real solvate CLI consumers must run on the target")
        package = Path(self.dependencies["solvate"].package_folder)
        output = Path(tempfile.mkdtemp(prefix="checkpoint-validation-", dir=self.build_folder)) / "results"
        command = [sys.executable, str(Path(self.source_folder)/"verify_checkpoint.py"),
                   "--binary", str(package/"bin/solvate"),
                   "--data", str(package/"share/solvate"),
                   "--output", str(output),
                   "--environment", "Conan-target-package"]
        self.run(" ".join(shlex.quote(arg) for arg in command), env="conanrun")
