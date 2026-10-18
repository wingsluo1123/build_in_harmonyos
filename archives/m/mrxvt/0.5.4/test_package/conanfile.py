#!/usr/bin/env python3
"""Conan test_package for mrxvt 0.5.4 (installed bin/mrxvt).

mrxvt is an X11 tabbed terminal emulator, so its real job needs a display
server.  Everything that happens before XOpenDisplay() (init.c:1062) does not:
the version banner, the options table and the "Error opening display" path,
which is itself a real dynamic-linkage check because the message cannot be
produced unless libX11/libXft/libfontconfig were loaded.

test_mrxvt.sh performs those checks on the packaged program.  Two of them read
the ELF header directly and therefore hold on any host; the runtime checks are
skipped - reported as SKIP, never as PASS - when the loader cannot start the
program at all, which is what a cross-build host does to an aarch64 binary
(exit 126/127 after "Error relocating .../libX11.so.6: __fd_chk").
"""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class MrxvtTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["mrxvt"]
        exe = os.path.join(package.package_folder, "bin", "mrxvt")
        if not os.path.isfile(exe):
            raise Exception("program not packaged: " + exe)

        script = os.path.join(self.recipe_folder, "test_mrxvt.sh")
        if not os.path.isfile(script):
            raise Exception("test script not found: " + script)

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so the
        # script is driven by bash when the target has one.
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            shell = "/bin/sh"

        # e_machine the recipe must emit: 183 = EM_AARCH64 (settings arch
        # armv8), 62 = EM_X86_64.
        machine = "62" if str(self.settings.arch) == "x86_64" else "183"

        # can_run() is recorded for the log only: the script, not the recipe,
        # decides which checks the running host can carry out.
        runnable = "yes" if can_run(self) else "no"

        # self.run() raises when the script exits non-zero.
        self.run("MRXVT_BIN={} MRXVT_EXPECT_MACHINE={} MRXVT_CAN_RUN={} {} {}".format(
            shlex.quote(exe), machine, runnable,
            shlex.quote(shell), shlex.quote(script)), env="conanrun")
