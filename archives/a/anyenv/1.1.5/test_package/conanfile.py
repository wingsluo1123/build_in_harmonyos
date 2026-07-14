#!/usr/bin/env python3
import os
import shutil
from tempfile import TemporaryDirectory

from conan import ConanFile
from conan.tools.build import can_run


class AnyenvTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def package_id(self):
        self.info.clear()

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["anyenv"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        test_script = os.path.join(self.source_folder, "test.sh")
        bash_path = shutil.which("bash") or os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
        bash_dir = os.path.dirname(bash_path) if bash_path else ""
        path_parts = [bin_dir]
        if bash_dir:
            path_parts.append(bash_dir)
        path_parts.append("$PATH")

        with TemporaryDirectory(prefix="anyenv-root-") as anyenv_root:
            env_prefix = f'ANYENV_ROOT="{anyenv_root}" PATH="{":".join(path_parts)}"'
            self.run(f'{env_prefix} "{bash_path}" "{test_script}"', env="conanrun")
