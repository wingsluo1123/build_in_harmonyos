import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class PerlMailtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _perl_bin(self):
        perl = os.environ.get("PERL")
        if perl and os.path.isfile(perl):
            return perl
        return shutil.which("perl") or "perl"

    def _shell(self):
        shell = os.environ.get("CONFIG_SHELL")
        if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
            return shell
        return shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skipping runtime test")
            return
        script = os.path.join(self.source_folder, "test_mailtools.sh")
        perl = self._perl_bin()
        shell = self._shell()
        self.run(
            f"{shlex.quote(shell)} {shlex.quote(script)}",
            env="conanrun",
        )
