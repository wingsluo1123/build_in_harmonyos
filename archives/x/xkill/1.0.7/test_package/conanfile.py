#!/usr/bin/env python3
"""Consumer test for the packaged xkill executable."""

import os
import shlex
import sys

from conan import ConanFile


class XkillTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _find_shared_object(dep, prefix):
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for name in sorted(files):
                if name.startswith(prefix):
                    hits.append(os.path.join(root, name))
        for path in hits:
            if not os.path.islink(path):
                return path
        return hits[0] if hits else None

    def _runtime_preload(self):
        preload = []
        for name, soname in (
            ("libxau", "libXau.so.6"),
            ("libxdmcp", "libXdmcp.so.6"),
            ("libxcb", "libxcb.so.1"),
            ("libx11", "libX11.so.6"),
            ("libxmu", "libXmuu.so.1"),
        ):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            path = self._find_shared_object(dep, soname)
            if path:
                preload.append(path)
        return ":".join(preload)

    def test(self):
        binary = os.path.join(self.dependencies["xkill"].package_folder, "bin", "xkill")
        script = os.path.join(self.source_folder, "test_xkill.py")
        preload = self._runtime_preload()
        self.output.info(f"xkill runtime LD_PRELOAD={preload}")
        command = " ".join(
            shlex.quote(item) for item in (sys.executable, script, binary, preload)
        )
        self.run(command, env="conanrun")
