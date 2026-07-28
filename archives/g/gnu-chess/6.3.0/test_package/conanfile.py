#!/usr/bin/env python3
"""Run GNU Chess command-line and UCI protocol checks."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GnuChessTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        binary = os.path.join(
            self.dependencies["gnu-chess"].package_folder, "bin", "gnuchess"
        )
        commands = os.path.join(self.source_folder, "uci-input.txt")
        output = os.path.join(self.build_folder, "uci-output.txt")

        self.run(f'"{binary}" --version', env="conanrun")
        self.run(f'"{binary}" --help > /dev/null', env="conanrun")
        self.run(
            f'"{binary}" --uci < "{commands}" > "{output}"',
            env="conanrun",
        )

        with open(output, encoding="utf-8", errors="replace") as stream:
            response = stream.read()
        if "uciok" not in response or "readyok" not in response:
            raise RuntimeError(f"GNU Chess UCI handshake failed:\n{response}")
