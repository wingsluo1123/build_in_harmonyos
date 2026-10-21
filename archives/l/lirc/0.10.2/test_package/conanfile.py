#!/usr/bin/env python3
"""Consumer test for the HarmonyOS lirc package.

Three independent checks run against the *installed* package:

1. ``test_lirc`` links ``liblirc_client`` and drives its real API:
   ``lirc_readconfig_only()`` parses a lircrc written by the test and
   ``lirc_code2char()`` maps a decoded remote code back to a string.
2. ``lircd --version`` must report the packaged version (0.10.2) — a version
   fingerprint read from the produced artifact, not from the recipe.
3. ``lirc-lsplugins -U <plugindir>`` must enumerate **every** installed
   hardware plugin with **zero load failures**.  The enumeration expands one
   ``.so`` into one line per driver name, so the line count is not the plugin
   count; the check is therefore (a) no line carries the ``F--`` failure flag
   and no ``# Error:`` line is emitted, and (b) the set of ``.so`` paths in the
   listing equals the set of ``.so`` files on disk.  A line count alone would
   accept a plugin the dynamic loader refuses (``default.so`` used to be
   unloadable: an undefined ``major`` symbol).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LircTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer test compiled and linked")
            return

        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run("{} -c './test_lirc'".format(bash), env="conanrun")

        tested = self.dependencies[self.tested_reference_str]
        package_folder = tested.package_folder
        lircd = os.path.join(package_folder, "bin", "lircd")
        lsplugins = os.path.join(package_folder, "bin", "lirc-lsplugins")
        plugindir = os.path.join(package_folder, "lib", "lirc", "plugins")

        version_log = os.path.join(self.build_folder, "lircd-version.txt")
        self.run(
            "{} --version 2>&1 | tee {}".format(lircd, version_log), env="conanrun"
        )
        text = open(version_log, encoding="utf-8", errors="replace").read()
        if "lircd 0.10.2" not in text:
            raise ConanException(
                "packaged lircd does not report version 0.10.2: {!r}".format(text)
            )
        self.output.info("PASS: packaged lircd reports version 0.10.2")

        plugins_log = os.path.join(self.build_folder, "lirc-lsplugins.txt")
        self.run(
            "{} -U {} -q 2>&1 | tee {}".format(lsplugins, plugindir, plugins_log),
            env="conanrun",
        )
        text = open(plugins_log, encoding="utf-8", errors="replace").read()
        lines = text.splitlines()
        load_failures = [
            line for line in lines
            if "F--" in line or line.lstrip().startswith("#")
        ]
        if load_failures:
            raise ConanException(
                "lirc-lsplugins reported plugin load failures:\n{}".format(
                    "\n".join(load_failures)
                )
            )
        enumerated = {
            os.path.basename(line.split()[-1])
            for line in lines
            if line.strip() and not line.startswith(("Warning",))
            and line.split() and line.split()[-1].endswith(".so")
        }
        on_disk = {os.path.basename(path) for path in glob.glob(
            os.path.join(plugindir, "*.so"))}
        if enumerated != on_disk:
            raise ConanException(
                "lirc-lsplugins did not enumerate the installed plugin set:\n"
                "  missing from listing: {}\n  not on disk: {}".format(
                    sorted(on_disk - enumerated), sorted(enumerated - on_disk)
                )
            )
        listed = [line for line in lines
                  if line.strip() and not line.startswith(("Warning",))]
        if len(listed) < 20:
            raise ConanException(
                "lirc-lsplugins enumerated only {} driver entries:\n{}".format(
                    len(listed), text
                )
            )
        self.output.info(
            "PASS: lirc-lsplugins listed {} driver entries from the {} packaged "
            "plugins, 0 load failures".format(len(listed), len(on_disk))
        )
