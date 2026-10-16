import os
import shlex
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class MrtparseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py", "upstream_samples.py", "samples-expected.json", "MANIFEST.yml"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("mrtparse target consumer cannot run")
        package = self.dependencies["mrtparse"].package_folder
        module_root = os.path.join(package, "lib", "python")
        for script in ("functional.py", "upstream_samples.py"):
            command = [sys.executable, "-B", os.path.join(self.source_folder, script), module_root,
                       os.path.join(self.build_folder, script.replace(".py", "-results.json"))]
            quoted = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
            self.run(quoted, env="conanrun")
