import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        test_dir = self.source_folder
        if not os.path.exists(os.path.join(test_dir, "test_scripts.sh")):
            test_dir = self.recipe_folder
        script = os.path.join(test_dir, "test_scripts.sh")
        self.run('sh "%s" "%s"' % (script, dep.package_folder.replace("\\", "/")),
                 env="conanrun")
