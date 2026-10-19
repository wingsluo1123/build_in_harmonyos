import os
from conan import ConanFile


class HaserlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        haserl = os.path.join(self.dependencies["haserl"].cpp_info.bindir, "haserl")
        runner = os.path.join(self.recipe_folder, "run_consumer_tests.sh")
        self.run('sh "%s" "%s"' % (runner, haserl), env="conanrun")
