import os
import shlex
import tempfile

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class TangTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # tangd-keygen invokes jose from PATH; the consumer graph must declare
        # the CLI itself instead of inheriting it from tang's build context.
        self.tool_requires("jose/15")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def test(self):
        tang = self.dependencies["tang"]
        bindir = os.path.join(tang.package_folder, "bin")
        libexecdir = os.path.join(tang.package_folder, "libexec")
        daemon_dir = bindir if os.path.isfile(os.path.join(bindir, "tangd")) else libexecdir
        for binary in ("tang-show-keys", "tangd", "tangd-keygen"):
            directory = bindir if binary == "tang-show-keys" else daemon_dir
            path = os.path.join(directory, binary)
            if not os.path.isfile(path):
                raise RuntimeError(f"Tang package is missing {path}")

        workdir = tempfile.mkdtemp(prefix="tang-consumer-", dir=self.build_folder)
        script = os.path.join(self.source_folder, "test_tang.sh")
        self.run(
            "sh {} {} {} {}".format(
                shlex.quote(script),
                shlex.quote(bindir),
                shlex.quote(daemon_dir),
                shlex.quote(workdir),
            ),
            cwd=self.build_folder,
            env="conanbuild",
        )
