"""Test package for git-secrets 1.3.0 (bash smoke test)."""
import os
import shlex
from conan import ConanFile


class GitSecretsTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["git-secrets"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifact with the real smoke test
        self.run(f"bash test_git_secrets.sh {shlex.quote(bin_dir)}", env="conanrun")
        self.output.info("git-secrets: OK")
