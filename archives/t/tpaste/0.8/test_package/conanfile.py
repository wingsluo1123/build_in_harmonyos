import os
import shutil

from conan import ConanFile


class TpasteTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["tpaste"]
        script = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "tpaste")
        if not os.path.isfile(script):
            raise RuntimeError(f"Expected packaged script is missing: {script}")
        # tpaste 是与架构无关的 POSIX sh 脚本，可直接用构建机的 sh 运行
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "sh"
        test_script = os.path.join(self.source_folder, "test_tpaste.sh")
        self.run(f'"{shell}" "{test_script}" "{script}"')
