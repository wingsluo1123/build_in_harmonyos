#!/usr/bin/env python3
"""Exercise memtool against a temporary regular file."""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class MemtoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        binary = os.path.join(
            self.dependencies["memtool"].package_folder, "bin", "memtool"
        )
        self.run(f'"{binary}" -V', env="conanrun")
        with tempfile.TemporaryDirectory(
            prefix="memtool-test-",
            dir=os.environ.get("TMPDIR"),
        ) as temporary:
            data = os.path.join(temporary, "memory.bin")
            output = os.path.join(temporary, "read.txt")
            self.run(
                f'"{binary}" mw -b -d "{data}" 0 0x41 0x42 0x43 0x44',
                env="conanrun",
            )
            self.run(
                f'"{binary}" md -b -d "{data}" 0+4 > "{output}"',
                env="conanrun",
            )
            with open(output, encoding="utf-8") as stream:
                rendered = stream.read().lower()
        if "41 42 43 44" not in rendered:
            raise RuntimeError(f"memtool file round-trip failed:\n{rendered}")
