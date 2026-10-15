#!/usr/bin/env python3
"""Consumer test package for exfatprogs 1.4.3.

The upstream tools are exercised end to end on a **regular file image**: on
this platform `mkfs.exfat`, `fsck.exfat`, `dump.exfat` and `exfatlabel`
support the S_ISREG path (the code only consults `/sys/dev/block` after
`S_ISBLK()` succeeds), so no block device, no loop device and no root
privileges are required.  The block-device and mount faces are not part of
the deliverable surface here and are deliberately not asserted.
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

TOOLS = (
    "mkfs.exfat",
    "fsck.exfat",
    "tune.exfat",
    "exfatlabel",
    "dump.exfat",
    "exfat2img",
)


class ExfatprogsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindirs = self.dependencies["exfatprogs"].cpp_info.bindirs
        if not bindirs:
            raise ConanException("exfatprogs reports no bindirs")
        bindir = bindirs[0]
        for tool in TOOLS:
            path = os.path.join(bindir, tool)
            if not os.path.isfile(path):
                raise ConanException(f"missing packaged executable: {path}")
        if not can_run(self):
            self.output.info(
                "cross build: packaged executables exist; runtime validation "
                "happens on the HarmonyOS PC device"
            )
            return
        script = os.path.join(self.source_folder, "test_exfatprogs.py")
        self.run(f'"{sys.executable}" "{script}" "{bindir}"', env="conanrun")
