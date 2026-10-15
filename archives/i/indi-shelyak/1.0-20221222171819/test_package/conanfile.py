#!/usr/bin/env python3
"""test_package for indi-shelyak 1.0-20221222171819 — runs the substantive
consumer probe (test_shelyak.py) against the installed package.

The two shipped artifacts are OHOS aarch64 INDI driver executables. They cannot
be executed on the build/CI host (E537/R49: HMDFS cannot mmap OHOS shared
libraries PROT_EXEC — execve returns EPERM even with the full SDK C++ runtime
and libindi package libs on LD_LIBRARY_PATH; same limitation libindi/libfli
document). So the probe verifies the delivered package substantively instead:
ELF64/AArch64 identity, DT_NEEDED linkage to libindidriver/AlignmentDriver,
and the indi_shelyak.xml registration file. See test_shelyak.py header.
"""
import os

from conan import ConanFile


class IndishelyakTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["indi-shelyak"].package_folder
        probe = os.path.join(self.recipe_folder, "test_shelyak.py")
        python = os.environ.get("PYTHON", "python3")
        # Use bash to run python3 (OHOS /system/bin/sh cannot always exec
        # scripts directly; CONFIG_SHELL wraps it — same as 2048.c test).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        os.environ["SHELYAK_PKG_DIR"] = pkg
        self.run(f"{bash} -c '\"{python}\" \"{probe}\"'", scope="build")
