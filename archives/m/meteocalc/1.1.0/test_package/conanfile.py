import os
import sys
import shlex
import subprocess
import inspect
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class MeteocalcTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        root = os.path.join(self.dependencies["meteocalc"].package_folder,
                            "site-packages")
        arguments = [sys.executable, os.path.join(self.source_folder, "test.py"), root]
        command = subprocess.list2cmdline(arguments) if os.name == "nt" else shlex.join(arguments)
        parameters = inspect.signature(self.run).parameters
        options = {"cwd": self.build_folder}
        if "ignore_errors" in parameters:
            options["ignore_errors"] = False
        elif "check" in parameters:
            options["check"] = True
        self.run(command, **options)
