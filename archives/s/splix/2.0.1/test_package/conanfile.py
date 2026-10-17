#!/usr/bin/env python3
"""Consumer test for splix 2.0.1 — executes the installed CUPS filters.

The test drives the two delivered executables the way cupsd would
(job-id, user, title, copies, options, [file]) and asserts on their exit codes
and output.  ``rastertoqpdl`` is fed a real (empty) CUPS raster stream so the
PPD parser, the request loader and the raster reader are all entered; the
missing raster data must make the filter fail *after* those stages instead of
silently succeeding.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class SplixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # Cross build: the OHOS filters cannot be executed on the build host.
            return
        package_folder = self.dependencies["splix"].package_folder
        script = os.path.join(self.recipe_folder, "test_splix.sh")
        # The CUPS raster page is stored as base64 text (sample-8x8.raster.b64)
        # instead of a binary blob: the platform cannot carry binary patch data
        # in a PR diff and rejects the whole PR with
        #   "error: missing binary patch data for '.../sample-8x8.raster'"
        # So it is decoded here, at run time, into byte-identical content and
        # handed to the script as a second argument.
        raster = self._materialise_sample_raster()
        # /system/bin/sh (mksh) cannot exec ELF files on OHOS, so use the
        # configured shell when it is available.
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        self.run(
            '"{}" "{}" "{}" "{}"'.format(shell, script, package_folder, raster),
            env="conanrun",
        )

    def _materialise_sample_raster(self):
        """Decode sample-8x8.raster.b64 into a byte-identical temporary file.

        Returns the path of the decoded raster.  The recorded sha256 is checked
        after decoding so a corrupted/edited text file fails loudly instead of
        silently feeding the filter different bytes.
        """
        import base64
        import hashlib
        import tempfile

        source = os.path.join(self.recipe_folder, "sample-8x8.raster.b64")
        wanted = None
        chunks = []
        with open(source, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line.startswith("#"):
                    marker = "sha256 "
                    if marker in line:
                        wanted = line.split(marker, 1)[1].strip()
                    continue
                if line:
                    chunks.append(line)
        raw = base64.b64decode("".join(chunks))
        digest = hashlib.sha256(raw).hexdigest()
        if wanted and digest != wanted:
            raise ConanException(
                "sample-8x8.raster.b64 decoded to sha256 %s but the file "
                "declares %s" % (digest, wanted))
        path = os.path.join(tempfile.mkdtemp(prefix="splix-raster-"),
                            "sample-8x8.raster")
        with open(path, "wb") as handle:
            handle.write(raw)
        self.output.info("splix test: decoded %d bytes of CUPS raster "
                         "(sha256 %s) to %s" % (len(raw), digest, path))
        return path
