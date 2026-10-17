import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class QsoasTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        package_folder = self.dependencies["qsoas"].package_folder
        executable = os.path.join(package_folder, "bin", "qsoas")
        if not os.path.isfile(executable):
            raise RuntimeError("packaged qsoas executable is missing")

        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        header = subprocess.run(
            [readelf, "-h", executable], check=True, capture_output=True,
            text=True, timeout=30,
        ).stdout
        if "AArch64" not in header:
            raise RuntimeError("packaged qsoas is not an AArch64 ELF")
        dynamic = subprocess.run(
            [readelf, "-d", executable], check=True, capture_output=True,
            text=True, timeout=30,
        ).stdout
        if "RPATH" in dynamic or "RUNPATH" in dynamic:
            raise RuntimeError("packaged qsoas contains a runtime search path")
        sections = subprocess.run(
            [readelf, "-SW", executable], check=True, capture_output=True,
            text=True, timeout=30,
        ).stdout
        if sum(".codesign" in line for line in sections.splitlines()) != 1:
            raise RuntimeError("packaged qsoas must contain one .codesign section")
        with open(executable, "rb") as handle:
            binary = handle.read()
        for marker in (b"/storage/Users/", b"/home/", b"/.conan2/", b"/.cache/"):
            if marker in binary:
                raise RuntimeError(
                    f"packaged qsoas contains a private build path marker: {marker!r}"
                )

        if not can_run(self):
            self.output.info("cross-run unavailable; ELF delivery checks completed")
            return

        python = shutil.which("python3")
        if not python:
            raise RuntimeError("python3 is required to drive the consumer test")
        script = os.path.join(self.source_folder, "test_qsoas.py")
        self.run(
            shlex.join([python, script, executable, self.source_folder]),
            env="conanrun",
        )
