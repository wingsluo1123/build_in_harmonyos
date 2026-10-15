#!/usr/bin/env python3
"""Conan test package for sortmerna 4.3.7."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class SortmernaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sortmerna test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # Cross build on a macOS dev box: OHOS binaries cannot execute
            # here; the real run happens on the HarmonyOS CI worker.
            self.output.info(
                "skip run: cross-built OHOS binaries cannot execute on the "
                "build host (can_run=False)"
            )
            return
        script = os.path.join(self.recipe_folder, "test_sortmerna.sh")
        shell = os.environ.get("CONFIG_SHELL") or "sh"
        binary = os.path.join(
            self.dependencies["sortmerna"].package_folder,
            "bin",
            "sortmerna",
        )
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"sortmerna binary not found in package: {binary}"
            )
        # S8 needs gzipped paired-end FASTQ. .gz artifacts are barred from the
        # PR (preflight no-binaries gate), so synthesize them here from the
        # shipped upstream test_read.fasta (the read is known to align to
        # test_ref.fasta: upstream t0 expects exactly 1 hit).
        import gzip
        import tempfile

        fasta = os.path.join(self.recipe_folder, "data", "test_read.fasta")
        with open(fasta) as fh:
            lines = fh.read().splitlines()
        rid = lines[0][1:].split()[0]
        seq = "".join(lines[1:])
        gz_dir = tempfile.mkdtemp(prefix="sortmerna-gz-")
        for mate in ("1", "2"):
            fq = os.path.join(gz_dir, f"reads_{mate}.fastq.gz")
            with gzip.open(fq, "wt") as out:
                out.write(f"@{rid}/{mate}\n{seq}\n+\n{'I' * len(seq)}\n")
        self.run(
            f'"{shell}" "{script}" "{binary}" "{gz_dir}"', env="conanrun"
        )
