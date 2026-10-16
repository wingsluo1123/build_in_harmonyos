import os

from conan import ConanFile


class VeraCryptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        import shutil
        shell = os.environ.get("CONFIG_SHELL")
        if not shell or not os.path.isfile(shell):
            shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{shell}" "{script}"', env="conanrun")