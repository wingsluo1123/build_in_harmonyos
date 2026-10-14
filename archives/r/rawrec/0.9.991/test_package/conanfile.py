#!/usr/bin/env python3
"""test_package for rawrec executable — runs test.sh which invokes the binary."""

import os
import shutil

from conan import ConanFile


class RawrecTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_shell(self):
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL")):
            if not cand:
                continue
            if os.path.isabs(cand):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except OSError:
                    continue
            else:
                found = shutil.which(cand)
                if found:
                    return found
        for abs_p in ("/bin/sh", "/system/bin/sh", "/data/service/hnp/bin/bash"):
            try:
                if os.path.isfile(abs_p) and os.access(abs_p, os.X_OK):
                    return abs_p
            except OSError:
                continue
        return shutil.which("sh") or shutil.which("bash") or "sh"

    def test(self):
        sh = self._resolve_shell()
        self.run("{} test.sh".format(sh), env="conanrun")
