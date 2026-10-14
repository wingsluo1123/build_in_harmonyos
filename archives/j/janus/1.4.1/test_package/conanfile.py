import os
import shlex
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class JanusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        janus = self.dependencies["janus"]
        executable = Path(janus.package_folder) / "bin" / "janus"
        if not executable.is_file():
            raise ConanException(f"Janus executable missing from package: {executable}")

        image = executable.read_bytes()[:20]
        if len(image) != 20 or image[:4] != b"\x7fELF":
            raise ConanException("Janus executable is not an ELF binary")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) == "armv8":
            if image[4] != 2 or image[5] != 1 or int.from_bytes(image[18:20], "little") != 183:
                raise ConanException("Janus package is not ELF64 little-endian AArch64")

        can_execute = can_run(self)
        if can_execute:
            self.run(f'"{executable}" --version', env="conanrun")

        target = os.environ.get("JANUS_HDC_TARGET")
        native_ohos = (
            str(self.settings.os) == "OHOS"
            and str(self.settings.arch) == "armv8"
            and can_execute
        )
        if target or native_ohos:
            script = Path(self.source_folder) / "test_janus_harmonyos.py"
            command = [sys.executable, str(script), "--janus-package", janus.package_folder]
            if native_ohos and not target:
                command.append("--native-device")
            if target:
                command.extend(["--target", target])
                hdc = os.environ.get("JANUS_HDC")
                if hdc:
                    command.extend(["--hdc", hdc])
            for dependency in self.dependencies.host.values():
                if dependency.ref.name != "janus":
                    command.extend(["--dependency-package", dependency.package_folder])
            self.run(shlex.join(command), env="conanrun")
        elif not can_execute:
            self.output.info(
                "Target executable is aarch64 and this host cannot run it; "
                "runtime execution is covered by the HDC HarmonyOS test."
            )
