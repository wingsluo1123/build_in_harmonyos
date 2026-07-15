import os

from conan import ConanFile
from conan.tools.build import can_run


class RedisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary
        dep = self.dependencies["redis"]
        redis_server = os.path.join(dep.package_folder, "bin", "redis-server")
        redis_cli = os.path.join(dep.package_folder, "bin", "redis-cli")
        if can_run(self):
            self.run(f'"{redis_server}" --version', env="conanrun")
            self.run(f'"{redis_cli}" --version', env="conanrun")
