#!/usr/bin/env python3
import os
import shutil
import tempfile

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
        anyenv_cmd = os.path.join(bin_dir, "anyenv")
        anyenv_root = tempfile.mkdtemp(prefix="anyenv-root-")
        bash_path = shutil.which("bash") or os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
        bash_dir = os.path.dirname(bash_path) if bash_path else ""
        path_parts = [bin_dir]
        if bash_dir:
            path_parts.append(bash_dir)
        path_parts.append("$PATH")
        env_prefix = f'ANYENV_ROOT="{anyenv_root}" PATH="{":".join(path_parts)}"'

        self.run(f'{env_prefix} "{anyenv_cmd}" -v', env="conanrun")
        self.run(f'{env_prefix} "{anyenv_cmd}" commands | grep "^version$"', env="conanrun")
        self.run(f'{env_prefix} "{anyenv_cmd}" help version | grep "Usage: anyenv version"', env="conanrun")
        self.run(f'{env_prefix} "{anyenv_cmd}" root | grep "{anyenv_root}"', env="conanrun")
