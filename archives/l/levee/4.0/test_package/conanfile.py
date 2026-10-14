#!/usr/bin/env python3
"""Consumer test for the packaged levee editor.

test.sh drives bin/levee with scripted keystrokes (8 functional checks and
negative controls) and runs the HarmonyOS consumer flow: levee edits
consumer.c.in, the profile's OHOS compiler builds the edited source and the
program verifies every edit.  See MANIFEST.yml for the case list.
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class LeveeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # levee links libncursesw statically, but the terminfo database it
        # reads at run time ships in the ncurses package (share/terminfo);
        # require it so that package folder is installed and resolvable.
        self.requires("ncurses/6.6")

    def layout(self):
        # keeps the test work directory out of the recipe folder
        basic_layout(self)

    def test(self):
        levee = os.path.join(self.dependencies["levee"].package_folder, "bin", "levee")
        terminfo = os.path.join(
            self.dependencies["ncurses"].package_folder, "share", "terminfo")
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc:
            raise ConanException("profile has no tools.build:compiler_executables c")
        # OHOS /system/bin/sh (mksh) cannot run the script reliably; use bash.
        bash = (shutil.which("bash") or os.environ.get("CONFIG_SHELL")
                or "/data/service/hnp/bin/bash")
        args = [bash, os.path.join(self.source_folder, "test.sh"), levee, terminfo,
                cc, self.source_folder, os.path.join(self.build_folder, "levee-test")]
        self.run(" ".join(shlex.quote(arg) for arg in args), env="conanrun")

        upstream = {
            "status": "no_tests", "framework": "none", "discovered": 0,
            "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
            "reason": "upstream ships no test directory and Makefile.in has no check/test target",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, separators=(",", ":")))
