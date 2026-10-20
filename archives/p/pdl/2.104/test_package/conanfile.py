from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # 实际断言放在 test_pdl.sh（CI 的 L0c 要求 test_package/ 下有 .sh 测试源文件）。
        if not can_run(self):
            return
        script = os.path.join(self.recipe_folder, "test_pdl.sh")
        self.run('sh "' + script + '"', env="conanrun")
