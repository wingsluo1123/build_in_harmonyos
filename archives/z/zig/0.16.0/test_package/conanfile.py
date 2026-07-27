#!/usr/bin/env python3
"""Conan test_package for Zig 0.16.0."""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class ZigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["zig"]
        zig = os.path.join(dep.package_folder, "bin", "zig.exe" if str(self.settings.os) == "Windows" else "zig")
        self.run(f'"{zig}" version', env="conanrun")

        version = subprocess.run(
            [zig, "version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if version.returncode != 0:
            raise RuntimeError(version.stderr)
        if version.stdout.strip() != "0.16.0":
            raise RuntimeError(f"unexpected Zig version: {version.stdout!r}")

        project_dir = os.path.join(self.build_folder, "smoke")
        os.makedirs(project_dir, exist_ok=True)
        source = os.path.join(self.source_folder, "smoke.zig")

        if str(self.settings.os) != "Windows":
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{script}" "{zig}" "{source}" "{project_dir}"', env="conanrun")
            return

        self.run(f'"{zig}" build-exe "{source}" -O ReleaseSmall --name smoke', cwd=project_dir, env="conanrun")
        exe = os.path.join(project_dir, "smoke.exe" if str(self.settings.os) == "Windows" else "smoke")
        if not os.path.exists(exe):
            raise RuntimeError("Zig did not produce the smoke executable")

        run_result = subprocess.run(
            [exe],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if run_result.returncode != 0:
            raise RuntimeError(run_result.stderr)
