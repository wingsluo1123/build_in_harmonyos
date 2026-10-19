#!/usr/bin/env python3
"""HarmonyOS consumer test for the packaged kdoctools executables."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class KDocToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os != "OHOS":
            self.output.info("kdoctools test_package skipped: requires HarmonyOS")
            return
        if not can_run(self):
            self.output.info("cross-building without emulator: test_package skipped")
            return

        package = self.dependencies["kdoctools"]
        for tool in ("meinproc6", "checkXML6"):
            path = os.path.join(package.package_folder, "bin", tool)
            if not os.path.isfile(path):
                raise ConanException(
                    "packaged {} is missing: {}".format(tool, path)
                )

        env = Environment()
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                lib_dir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        # checkXML6 resolves meinproc6 through PATH
        env.prepend_path("PATH", os.path.join(package.package_folder, "bin"))
        env.define("QT_QPA_PLATFORM", "offscreen")

        script = os.path.join(self.source_folder, "test_ohos_docbook.py")
        command = "python3 {} {}".format(
            shlex.quote(script),
            shlex.quote(package.package_folder),
        )
        with env.vars(self).apply():
            # VirtualRunEnv carries the full transitive dependency graph
            # (e.g. libxml2) that self.dependencies.values() does not expose here.
            self.run(command, env="conanrun")
