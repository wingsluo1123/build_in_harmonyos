#!/usr/bin/env python3
"""Conan test_package — unhide 20240510.

Runs test_unhide.py against the packaged four unhide binaries
(bin/unhide-linux, bin/unhide_rb, bin/unhide-tcp, bin/unhide-posix):
ELF artefact checks (AArch64, OHOS NDK note, dynamically linked PIE with
NEEDED only libc.so — no static libc in the OHOS sysroot, sockstat 0.4.2
precedent, NX) plus the real CLI behaviour of each binary in the matching
execution mode (root: version / usage / getopt / live sysinfo+getpriority
scans; non-root — the CI device case: the upstream root-refusal path).
See test_unhide.py for the case list.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class UnhideTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bindir = os.path.join(self.dependencies["unhide"].package_folder, "bin")
        if not os.path.isdir(bindir):
            raise ConanException("bin/ not packaged")
        for binary in ("unhide-linux", "unhide_rb", "unhide-tcp", "unhide-posix"):
            if not os.path.isfile(os.path.join(bindir, binary)):
                raise ConanException("bin/%s not packaged" % binary)
        script = os.path.join(self.source_folder, "test_unhide.py")
        ohos = " --ohos" if str(self.settings.os) == "OHOS" else ""
        self.run(f'"{sys.executable}" "{script}" --bindir "{bindir}"{ohos}', env="conanrun")
