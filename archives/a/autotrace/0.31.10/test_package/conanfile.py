#!/usr/bin/env python3
"""Conan test package for autotrace 0.31.10."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class AutotraceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _run_checked(self, args, **kwargs):
        command = " ".join(shlex.quote(str(arg)) for arg in args)
        retcode = self.run(command, ignore_errors=True, **kwargs)
        if retcode not in (None, 0):
            raise RuntimeError(f"Command failed with exit code {retcode}: {command}")

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC") or "cc"
        run_binary = "1" if can_run(self) else "0"
        script = os.path.join(self.source_folder, "test_autotrace.py")
        pkg_config_paths = [
            os.path.join(pkg, "lib", "pkgconfig"),
            self.generators_folder,
        ]
        if os.environ.get("PKG_CONFIG_PATH"):
            pkg_config_paths.append(os.environ["PKG_CONFIG_PATH"])
        old_pkg_config_path = os.environ.get("PKG_CONFIG_PATH")
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_config_paths)
        try:
            self._run_checked(
                [sys.executable, script, pkg, cc, run_binary],
                env="conanrun",
            )
        finally:
            if old_pkg_config_path is None:
                os.environ.pop("PKG_CONFIG_PATH", None)
            else:
                os.environ["PKG_CONFIG_PATH"] = old_pkg_config_path
