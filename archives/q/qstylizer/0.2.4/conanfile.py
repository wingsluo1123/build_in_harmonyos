"""Pure Python QSS generation with token-aware declaration terminators."""
import hashlib
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, unzip
from conan.tools.layout import basic_layout


class QstylizerConan(ConanFile):
    name = 'qstylizer'
    version = '0.2.4'
    license = 'MIT'
    description = 'Generate and parse Qt stylesheets while preserving literal semicolons'
    homepage = 'https://github.com/blambright/qstylizer'
    url = 'https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos'
    package_type = 'unknown'
    settings = 'os', 'arch', 'compiler', 'build_type'
    no_copy_source = True
    exports_sources = 'test_package/regression.py'

    def requirements(self):
        self.requires('python/3.12.9#d8eda770878152bea40b42db9f7024cd', libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def _fetch(self, data, destination=None, strip_root=False):
        inputs = os.getenv('QSTYLIZER_INPUTS')
        options = {'strip_root': strip_root, 'extract_filter': 'data'}
        if destination is not None:
            options['destination'] = destination
        if inputs:
            archive = os.path.join(inputs, data['url'].rsplit('/', 1)[-1])
            with open(archive, 'rb') as stream:
                if hashlib.sha256(stream.read()).hexdigest() != data['sha256']:
                    raise ConanException('qstylizer input SHA256 mismatch: ' + os.path.basename(archive))
            unzip(self, archive, **options)
        else:
            get(self, **data, **options)

    def source(self):
        self._fetch(self.conan_data['sources'][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        python = self.dependencies['python'].package_folder
        env = Environment()
        env.define('PYTHONHOME', python)
        env.prepend_path('PATH', os.path.join(python, 'bin'))
        env.prepend_path('LD_LIBRARY_PATH', os.path.join(python, 'lib'))
        env.define('PYTHONDONTWRITEBYTECODE', '1')
        env.define('PYTHONNOUSERSITE', '1')
        env.define('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
        env.define_path('PYTHONPATH', os.path.join(self.build_folder, 'build-tools'))
        env.prepend_path('PYTHONPATH', self.source_folder)
        env.vars(self).save_script('qstylizer-runtime')

    def build(self):
        tools = os.path.join(self.build_folder, 'build-tools')
        for group in ('runtime_wheels', 'test_wheels'):
            for wheel in self.conan_data[group].values():
                self._fetch(wheel, destination=tools)
        python = os.path.join(self.dependencies['python'].package_folder, 'bin', 'python3.12')
        command = [python, '-B', '-m', 'pytest', '-p', 'pytest_mock', '-q', '-o', 'addopts=']
        self.run(shlex.join(command + ['test']), cwd=self.source_folder, env='qstylizer-runtime')
        self.run(shlex.join(command + [os.path.join(self.source_folder, 'test_package', 'regression.py')]), cwd=self.source_folder, env='qstylizer-runtime')

    def package(self):
        destination = os.path.join(self.package_folder, 'lib', 'python')
        copy(self, '*.py', src=os.path.join(self.source_folder, 'qstylizer'), dst=os.path.join(destination, 'qstylizer'))
        copy(self, '*', src=os.path.join(self.source_folder, 'qstylizer.egg-info'), dst=os.path.join(destination, 'qstylizer.egg-info'))
        for wheel in self.conan_data['runtime_wheels'].values():
            self._fetch(wheel, destination=destination)
        copy(self, 'LICENSE.txt', src=self.source_folder, dst=os.path.join(self.package_folder, 'licenses'))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        python = self.dependencies['python'].package_folder
        self.runenv_info.define('PYTHONHOME', python)
        self.runenv_info.prepend_path('PATH', os.path.join(python, 'bin'))
        self.runenv_info.prepend_path('LD_LIBRARY_PATH', os.path.join(python, 'lib'))
        self.runenv_info.prepend_path('PYTHONPATH', os.path.join(self.package_folder, 'lib', 'python'))
