#!/usr/bin/env python3
"""test_package for handbrake 1.11.2 (HandBrakeCLI executable).

R34: the test really executes the packaged binary. HandBrakeCLI --version
prints compile-time hardening info and starts the libhb thread — this only
works if the packaged (self-signed) binary is present and runnable.

R45: normalize test.sh to LF before executing it. The Windows checkout can
materialize the shell script with CRLF, which zsh on OHOS treats as literal
characters.
"""
import os
import shutil

from conan import ConanFile


class HandbrakeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _host_shell():
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("zsh"),
            "/usr/bin/zsh",
            "/bin/sh",
            "/system/bin/sh",
        ):
            if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        return "sh"

    def _normalized_test_script(self):
        source_script = os.path.join(self.source_folder, "test.sh")
        build_script = os.path.join(self.build_folder, "test-lf.sh")
        with open(source_script, "rb") as src:
            content = src.read().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        with open(build_script, "wb") as dst:
            dst.write(content)
        os.chmod(build_script, 0o755)
        return build_script

    def test(self):
        # OHOS: wrap binary execution with an available host shell.
        shell = self._host_shell()
        # Conan 2.x explicit tests run in build_folder; keep the script LF-only.
        test_sh = self._normalized_test_script()
        # test.sh runs `HandBrakeCLI --version` inside the conanrun env (PATH
        # includes the packaged bin/). HandBrakeCLI returns 0 on --version.
        self.run(f'{shell} "{test_sh}"', env="conanrun")
