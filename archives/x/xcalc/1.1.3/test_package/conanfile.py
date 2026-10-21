#!/usr/bin/env python3
"""Consumer test for the packaged xcalc executable.

L1 test: executes the installed xcalc binary over its no-server code paths
(-version / -help, both handled in main() before XtAppInitialize opens a
display — see xcalc.c) and one no-display path (XtAppInitialize must fail
cleanly when no X server is reachable).  Real assertions on stdout/stderr and
the process exit code (R34).

Runtime closure: the OHOS loader may ignore LD_LIBRARY_PATH for Conan cache
paths, and the cache libs are symlink chains that HMFS materialises
unreliably (E050).  Every concrete (non-symlink) shared object of the
dependency graph is therefore passed to the test script as LD_PRELOAD, and the
Conan run environment (VirtualRunEnv) additionally supplies the libdirs.
"""

import os

from conan import ConanFile


class XcalcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _concrete_shared_objects(dependency):
        """Real (non-symlink) *.so* files inside a dependency package."""
        hits = []
        for root, _dirs, files in os.walk(dependency.package_folder):
            for name in sorted(files):
                if ".so" not in name:
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                hits.append(path)
        return hits

    def _runtime_preload(self):
        # Lower-level libraries first so LD_PRELOAD mirrors link order.
        order = {
            "libxau": 0,
            "libxdmcp": 1,
            "libxcb": 2,
            "libx11": 3,
            "libxext": 4,
            "libice": 5,
            "libsm": 6,
            "libxt": 7,
            "libxmu": 8,
            "libxpm": 9,
            "libxaw": 10,
        }
        preload = []
        for name, dependency in self.dependencies.items():
            if str(name).split("/")[0] not in order:
                continue
            preload.extend(self._concrete_shared_objects(dependency))
        preload.sort(key=lambda p: os.path.basename(p))
        return ":".join(dict.fromkeys(preload))

    def test(self):
        package = self.dependencies["xcalc"]
        binary = os.path.join(package.package_folder, "bin", "xcalc")
        import sys

        script = os.path.join(self.source_folder, "test_xcalc.py")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        import shlex

        command = " ".join(
            shlex.quote(item) for item in (sys.executable, script, binary, preload)
        )
        self.run(command, env="conanrun")
