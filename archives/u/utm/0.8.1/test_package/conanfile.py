#!/usr/bin/env python3
"""Run installed utm API and command tests."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class UtmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_dir = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.recipe_folder, "test_utm.py")
        self.run(f"{shlex.quote(sys.executable)} {shlex.quote(script)} "
                 f"{shlex.quote(package_dir)}", env="conanrun")
        if str(self.settings.os) == "OHOS":
            ohos_script = os.path.join(self.recipe_folder, "test_ohos.py")
            self.run(f"{shlex.quote(sys.executable)} {shlex.quote(ohos_script)} "
                     f"{shlex.quote(package_dir)}", env="conanrun")
