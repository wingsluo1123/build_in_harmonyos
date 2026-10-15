import os
import sys

from conan import ConanFile


class SqlparseTestConan(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["sqlparse"]
        module_dir = os.path.join(dep.package_folder, "lib", "python")
        script = os.path.join(self.source_folder, "test_sqlparse.py")
        self.run(f'"{sys.executable}" "{script}" "{module_dir}"')
