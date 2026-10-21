import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class SqlparseTestConan(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["sqlparse"]
        module_dir = os.path.join(dep.package_folder, "lib", "python")
        script = os.path.join(self.source_folder, "test_sqlparse.py")
        # 消费者测试直接从 package_folder 导入模块；禁用字节码写入，
        # 否则 test() 会把 __pycache__ 写回制品目录（实测 21 个 .pyc）。
        env = Environment()
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{script}" "{module_dir}"')
