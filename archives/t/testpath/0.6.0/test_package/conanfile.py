import os
import shlex
from pathlib import Path
from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv


class TestpathConsumer(ConanFile):
    settings = 'os', 'arch', 'compiler', 'build_type'
    test_type = 'explicit'

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        python = Path(self.dependencies['python'].package_folder) / 'bin/python3'
        root = self.dependencies['testpath'].package_folder
        e = Environment()
        e.define('PYTHONHOME', self.dependencies['python'].package_folder)
        e.define('PYTHONNOUSERSITE', '1')
        e.define('PYTHONDONTWRITEBYTECODE', '1')
        with e.vars(self).apply():
            self.run(shlex.join([
                str(python), '-B', os.path.join(self.source_folder, 'test.py'), root,
            ]), env='conanrun')
